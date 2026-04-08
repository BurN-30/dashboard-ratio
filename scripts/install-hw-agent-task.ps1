<#
.SYNOPSIS
    Installe le hw-agent TrackBoard en tache planifiee Windows auto-start.

.DESCRIPTION
    Cree une tache Task Scheduler "TrackBoard-hw-agent" qui :
    - Se lance au demarrage de Windows (avant le login user)
    - Tourne en compte SYSTEM (acces complet a WMI / LibreHardwareMonitor)
    - Redemarre automatiquement si le process crash (3 tentatives, intervalle 1 min)
    - Pas de limite de duree
    - Idempotent : si la tache existe deja, elle est mise a jour

    Necessite : PowerShell en mode Administrateur.

.PARAMETER HwAgentDir
    Chemin absolu du dossier hw-agent contenant agent.py, venv\, .env.
    Defaut : detection automatique relative au script.

.EXAMPLE
    # Lancer en admin :
    powershell.exe -ExecutionPolicy Bypass -File .\install-hw-agent-task.ps1

.EXAMPLE
    # Specifier le chemin manuellement :
    .\install-hw-agent-task.ps1 -HwAgentDir "C:\path\to\trackboard\hw-agent"
#>

[CmdletBinding()]
param(
    [string]$HwAgentDir = ""
)

$ErrorActionPreference = "Stop"
$TaskName = "TrackBoard-hw-agent"

# --- 1. Verification admin ---
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[ERREUR] Ce script doit etre lance en mode Administrateur." -ForegroundColor Red
    Write-Host "        Clic droit sur PowerShell -> Run as Administrator, puis relance." -ForegroundColor Yellow
    exit 1
}

# --- 2. Detection du dossier hw-agent ---
if (-not $HwAgentDir) {
    # Chercher dans les emplacements probables (relatif au script en priorite)
    $candidates = @(
        (Join-Path $PSScriptRoot "..\hw-agent"),
        "$env:USERPROFILE\trackboard\hw-agent",
        "C:\trackboard\hw-agent"
    )
    foreach ($c in $candidates) {
        if (Test-Path (Join-Path $c "agent.py")) {
            $HwAgentDir = (Resolve-Path $c).Path
            Write-Host "[OK] Detecte hw-agent dans : $HwAgentDir" -ForegroundColor Green
            break
        }
    }
}

if (-not $HwAgentDir -or -not (Test-Path (Join-Path $HwAgentDir "agent.py"))) {
    Write-Host "[ERREUR] Impossible de trouver agent.py. Specifie le chemin avec -HwAgentDir." -ForegroundColor Red
    exit 1
}

# --- 3. Verification du venv ---
$pythonExe = Join-Path $HwAgentDir "venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "[WARN] venv\Scripts\python.exe absent." -ForegroundColor Yellow
    Write-Host "       Creation du venv..." -ForegroundColor Yellow
    Push-Location $HwAgentDir
    try {
        & python -m venv venv
        & $pythonExe -m pip install --upgrade pip
        & $pythonExe -m pip install -r requirements.txt
    } finally {
        Pop-Location
    }
    if (-not (Test-Path $pythonExe)) {
        Write-Host "[ERREUR] Echec creation du venv." -ForegroundColor Red
        exit 1
    }
}

# --- 4. Verification du .env ---
$envFile = Join-Path $HwAgentDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "[ERREUR] $envFile absent. Cree-le depuis .env.example." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Configuration de la tache :" -ForegroundColor Cyan
Write-Host "  Nom         : $TaskName"
Write-Host "  Dossier     : $HwAgentDir"
Write-Host "  Python      : $pythonExe"
Write-Host "  Compte      : NT AUTHORITY\SYSTEM"
Write-Host "  Trigger     : At startup"
Write-Host "  Restart     : 3x intervalle 1 min"
Write-Host ""

# --- 5. Creation de la tache ---
$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument "agent.py" `
    -WorkingDirectory $HwAgentDir

$trigger = New-ScheduledTaskTrigger -AtStartup
# Petit delai pour laisser le reseau et LibreHardwareMonitor se lancer avant
$trigger.Delay = "PT30S"

$principal = New-ScheduledTaskPrincipal `
    -UserId "NT AUTHORITY\SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew

# Supprimer la tache existante si presente (idempotence)
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[INFO] Tache existante detectee, mise a jour..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Pousse les stats hardware vers le backend TrackBoard via WebSocket. Auto-start au boot, restart si crash." | Out-Null

Write-Host "[OK] Tache '$TaskName' creee." -ForegroundColor Green
Write-Host ""

# --- 6. Lancement immediat (test) ---
Write-Host "Lancement immediat pour test..." -ForegroundColor Cyan
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3

$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Host ""
Write-Host "Etat actuel :" -ForegroundColor Cyan
Write-Host "  State           : $($task.State)"
Write-Host "  LastRunTime     : $($info.LastRunTime)"
Write-Host "  LastTaskResult  : 0x$('{0:X}' -f $info.LastTaskResult) ($($info.LastTaskResult))"
Write-Host "  NumberOfMissedRuns: $($info.NumberOfMissedRuns)"
Write-Host ""

if ($info.LastTaskResult -ne 0 -and $task.State -ne "Running") {
    Write-Host "[WARN] La tache ne semble pas avoir demarre correctement." -ForegroundColor Yellow
    Write-Host "       Verifie l'historique dans Task Scheduler GUI :" -ForegroundColor Yellow
    Write-Host "       taskschd.msc -> Task Scheduler Library -> $TaskName -> History" -ForegroundColor Yellow
} else {
    Write-Host "[OK] Le hw-agent tourne. Verifie cote backend TrackBoard :" -ForegroundColor Green
    Write-Host "     curl https://api.<ton-domaine>/hardware/status" -ForegroundColor Green
    Write-Host "     Doit retourner agent_connected: true" -ForegroundColor Green
}

Write-Host ""
Write-Host "Pour gerer la tache plus tard :" -ForegroundColor Cyan
Write-Host "  Demarrer    : Start-ScheduledTask -TaskName $TaskName"
Write-Host "  Arreter     : Stop-ScheduledTask -TaskName $TaskName"
Write-Host "  Supprimer   : Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
Write-Host "  GUI         : taskschd.msc"
Write-Host ""
