<#
.SYNOPSIS
    Installe la tache planifiee Windows "TrackBoard-session-sync" (renouvellement de la
    session C411 sur TrackBoard), sous le compte de l'utilisateur courant, sans privilege.

.DESCRIPTION
    Cree une tache Task Scheduler qui lance session-sync\session_sync.py --navigateur :
    - tous les 6 jours a l'heure choisie (la session C411 dure 7 jours fixes) ;
    - sous le compte de l'utilisateur courant, jamais SYSTEM : RunLevel Limited,
      LogonType Interactive. La tache ne tourne que si l'utilisateur a une session Windows
      ouverte : c'est voulu, la fenetre du navigateur doit pouvoir s'afficher pour qu'il se
      connecte lui-meme a C411 (captcha compris) quand la session est a refaire ;
    - rattrapee au prochain demarrage de session si l'heure a ete manquee ;
    - limitee a 1 heure, une seule instance a la fois ;
    - idempotente : une tache existante est remplacee.

    A lancer dans un PowerShell ordinaire (PAS en administrateur) : la tache est enregistree
    pour le compte qui lance ce script. Aucun mot de passe Windows n'est demande ni stocke.

    Le script cree aussi le venv (session-sync\venv), installe les dependances et reserve
    la lecture de session-sync\.env au compte courant (il contient le jeton de depot de session).

.PARAMETER SessionSyncDir
    Chemin du dossier session-sync (session_sync.py, .env). Defaut : ..\session-sync.

.PARAMETER Heure
    Heure de lancement, au format HH:mm. Defaut : 19:00.

.PARAMETER SansVerification
    Ne lance pas le controle final (session_sync.py --verifier).

.EXAMPLE
    powershell.exe -ExecutionPolicy Bypass -File .\install-session-sync-task.ps1

.EXAMPLE
    .\install-session-sync-task.ps1 -Heure 21:30
#>

[CmdletBinding()]
param(
    [string]$SessionSyncDir = "",
    [ValidatePattern('^([01]\d|2[0-3]):[0-5]\d$')]
    [string]$Heure = "19:00",
    [switch]$SansVerification
)

$ErrorActionPreference = "Stop"
$TaskName = "TrackBoard-session-sync"
$JoursEntreDeuxLancements = 6

# --- 1. Compte : utilisateur courant, ni SYSTEM ni session elevee ---
$identite = [Security.Principal.WindowsIdentity]::GetCurrent()
$utilisateur = $identite.Name
if ($identite.IsSystem) {
    Write-Host "[ERREUR] Ce script ne s'installe pas sous le compte SYSTEM." -ForegroundColor Red
    Write-Host "         Relance-le dans ta propre session Windows." -ForegroundColor Yellow
    exit 1
}
$principalCourant = New-Object Security.Principal.WindowsPrincipal($identite)
if ($principalCourant.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[INFO] PowerShell lance en administrateur : inutile ici." -ForegroundColor Yellow
    Write-Host "       La tache sera quand meme enregistree sans privilege (RunLevel Limited)." -ForegroundColor Yellow
}

# --- 2. Dossier session-sync ---
if (-not $SessionSyncDir) {
    $SessionSyncDir = Join-Path $PSScriptRoot "..\session-sync"
}
if (-not (Test-Path (Join-Path $SessionSyncDir "session_sync.py"))) {
    Write-Host "[ERREUR] session_sync.py introuvable. Precise le dossier avec -SessionSyncDir." -ForegroundColor Red
    exit 1
}
$SessionSyncDir = (Resolve-Path $SessionSyncDir).Path
Write-Host "[OK] Dossier : $SessionSyncDir" -ForegroundColor Green

# --- 3. venv et dependances ---
$pythonExe = Join-Path $SessionSyncDir "venv\Scripts\python.exe"
$pythonwExe = Join-Path $SessionSyncDir "venv\Scripts\pythonw.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "[INFO] Creation du venv..." -ForegroundColor Yellow
    & python -m venv (Join-Path $SessionSyncDir "venv")
    if (-not (Test-Path $pythonExe)) {
        Write-Host "[ERREUR] Echec de la creation du venv (Python est-il dans le PATH ?)." -ForegroundColor Red
        exit 1
    }
}
& $pythonExe -m pip install --quiet --disable-pip-version-check -r (Join-Path $SessionSyncDir "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERREUR] Installation des dependances impossible." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Dependances installees" -ForegroundColor Green

# --- 4. .env : present, et lisible par le seul compte courant ---
$envFile = Join-Path $SessionSyncDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "[ERREUR] $envFile absent. Copie .env.example en .env et remplis-le." -ForegroundColor Red
    exit 1
}
& icacls $envFile /inheritance:r /grant:r "${utilisateur}:(R,W)" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Droits de $envFile non restreints (icacls a echoue)." -ForegroundColor Yellow
} else {
    Write-Host "[OK] .env reserve au compte $utilisateur" -ForegroundColor Green
}

# --- 5. Tache planifiee ---
# pythonw.exe : pas de console noire ; le script ecrit dans logs\session-sync.log.
$action = New-ScheduledTaskAction `
    -Execute $pythonwExe `
    -Argument "session_sync.py --navigateur" `
    -WorkingDirectory $SessionSyncDir

$trigger = New-ScheduledTaskTrigger -Daily -DaysInterval $JoursEntreDeuxLancements -At $Heure

# Compte courant, session interactive, jeton sans elevation. Ni SYSTEM, ni "Highest".
$principal = New-ScheduledTaskPrincipal `
    -UserId $utilisateur `
    -LogonType Interactive `
    -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -MultipleInstances IgnoreNew

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[INFO] Tache existante detectee, remplacement..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Renouvelle la session C411 de TrackBoard tous les 6 jours. Compte utilisateur, sans privilege. La connexion a C411 reste faite a la main dans la fenetre ouverte." | Out-Null

# --- 6. Controle de ce qui a ete enregistre ---
$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName
$p = $task.Principal

Write-Host ""
Write-Host "Tache enregistree :" -ForegroundColor Cyan
Write-Host "  Nom          : $TaskName"
Write-Host "  Compte       : $($p.UserId)"
Write-Host "  LogonType    : $($p.LogonType)"
Write-Host "  RunLevel     : $($p.RunLevel)"
Write-Host "  Declencheur  : tous les $JoursEntreDeuxLancements jours a $Heure"
Write-Host "  Prochain     : $($info.NextRunTime)"
Write-Host "  Commande     : $pythonwExe session_sync.py --navigateur"
Write-Host ""

if ("$($p.RunLevel)" -ne "Limited" -or "$($p.LogonType)" -ne "Interactive" -or "$($p.UserId)" -match '(?i)SYSTEM$|^S-1-5-18$') {
    Write-Host "[ERREUR] La tache n'a pas le compte ou le niveau attendus : suppression." -ForegroundColor Red
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    exit 1
}
Write-Host "[OK] Tache sans privilege, sous le compte utilisateur." -ForegroundColor Green

# --- 7. Controle de l'acces a TrackBoard (ne depose rien, n'ouvre pas de navigateur) ---
if (-not $SansVerification) {
    Write-Host ""
    Write-Host "Controle de l'acces a TrackBoard..." -ForegroundColor Cyan
    Push-Location $SessionSyncDir
    try {
        & $pythonExe session_sync.py --verifier
        $code = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($code -ne 0) {
        Write-Host "[WARN] Controle en echec (code $code) : corrige .env, puis relance" -ForegroundColor Yellow
        Write-Host "       $pythonExe $SessionSyncDir\session_sync.py --verifier" -ForegroundColor Yellow
    } else {
        Write-Host "[OK] TrackBoard joignable et jeton accepte." -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Pour gerer la tache plus tard :" -ForegroundColor Cyan
Write-Host "  Lancer maintenant : Start-ScheduledTask -TaskName $TaskName"
Write-Host "  Dernier resultat  : (Get-ScheduledTaskInfo -TaskName $TaskName).LastTaskResult"
Write-Host "  Journal           : Get-Content '$SessionSyncDir\logs\session-sync.log' -Tail 20"
Write-Host "  Supprimer         : Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
Write-Host ""
