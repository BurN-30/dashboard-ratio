<#
.SYNOPSIS
    Repare le service Windows cloudflared qui ne lit pas son config.yml.

.DESCRIPTION
    Probleme detecte sur pcnat : le service "cloudflared" tourne en compte
    LocalSystem et son ImagePath ne contient pas --config. Donc cloudflared
    cherche son config dans le profil de SYSTEM, soit
    C:\Windows\System32\config\systemprofile\.cloudflared\, qui n'existe pas.
    Resultat : le service tourne mais sans ingress rules valides, la colonne
    CONNECTIONS de "cloudflared tunnel list" est vide, tous les hostnames
    proxifies retournent HTTP 530.

    Ce script :
    1. Verifie les droits admin
    2. Localise les fichiers source dans $env:USERPROFILE\.cloudflared\
       (ou autre repertoire indique via -SourceDir)
    3. Stoppe le service cloudflared
    4. Desinstalle le service via "cloudflared service uninstall"
    5. Cree C:\Windows\System32\config\systemprofile\.cloudflared\ si absent
    6. Copie config.yml + *.json (credentials) + cert.pem vers le bon dossier
    7. Met a jour les paths absolus dans config.yml (credentials-file)
    8. Reinstalle le service via "cloudflared service install"
    9. Demarre le service
    10. Verifie l'etat et teste un endpoint exterieur

    Idempotent : peut etre relance plusieurs fois sans casser quoi que ce soit.

.PARAMETER SourceDir
    Dossier source contenant config.yml + credentials + cert.pem.
    Defaut : "$env:USERPROFILE\.cloudflared"

.PARAMETER CloudflaredExe
    Chemin du binaire cloudflared.exe.
    Defaut : recherche automatique, fallback "C:\Program Files (x86)\cloudflared\cloudflared.exe"

.PARAMETER TestHostname
    Hostname a tester apres le fix pour valider le tunnel (HTTP 200/401/302 attendu).
    Si non specifie, le test est skip. Exemple : "tautulli.mondomaine.fr"

.EXAMPLE
    powershell.exe -ExecutionPolicy Bypass -File .\fix-cloudflare-tunnel.ps1
    powershell.exe -ExecutionPolicy Bypass -File .\fix-cloudflare-tunnel.ps1 -TestHostname tautulli.mondomaine.fr
#>

[CmdletBinding()]
param(
    [string]$SourceDir = "$env:USERPROFILE\.cloudflared",
    [string]$CloudflaredExe = "",
    [string]$TestHostname = ""
)

$ErrorActionPreference = "Stop"

# --- 1. Verification admin ---
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[ERREUR] Ce script doit etre lance en mode Administrateur." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Mode admin confirme." -ForegroundColor Green

# --- 2. Localiser cloudflared.exe ---
if (-not $CloudflaredExe) {
    $candidates = @(
        "C:\Program Files (x86)\cloudflared\cloudflared.exe",
        "C:\Program Files\cloudflared\cloudflared.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) {
            $CloudflaredExe = $c
            break
        }
    }
    if (-not $CloudflaredExe) {
        $found = (Get-Command cloudflared.exe -ErrorAction SilentlyContinue).Source
        if ($found) { $CloudflaredExe = $found }
    }
}
if (-not $CloudflaredExe -or -not (Test-Path $CloudflaredExe)) {
    Write-Host "[ERREUR] cloudflared.exe introuvable. Specifie -CloudflaredExe." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] cloudflared.exe : $CloudflaredExe" -ForegroundColor Green
$cloudflaredVersion = (& $CloudflaredExe --version 2>&1) -join " "
Write-Host "    Version : $cloudflaredVersion" -ForegroundColor DarkGray

# --- 3. Verifier les fichiers source ---
if (-not (Test-Path $SourceDir)) {
    Write-Host "[ERREUR] Dossier source absent : $SourceDir" -ForegroundColor Red
    exit 1
}

$srcConfig = Join-Path $SourceDir "config.yml"
if (-not (Test-Path $srcConfig)) {
    Write-Host "[ERREUR] config.yml absent dans $SourceDir" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Source config.yml : $srcConfig" -ForegroundColor Green

$srcCert = Join-Path $SourceDir "cert.pem"
if (-not (Test-Path $srcCert)) {
    Write-Host "[WARN] cert.pem absent (peut etre OK selon ton setup)" -ForegroundColor Yellow
    $srcCert = $null
} else {
    Write-Host "[OK] Source cert.pem present" -ForegroundColor Green
}

$srcCredentials = Get-ChildItem -Path $SourceDir -Filter "*.json" -ErrorAction SilentlyContinue
if ($srcCredentials.Count -eq 0) {
    Write-Host "[ERREUR] Aucun fichier credentials *.json dans $SourceDir" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Source credentials JSON : $($srcCredentials.Count) fichier(s)" -ForegroundColor Green
foreach ($f in $srcCredentials) { Write-Host "    -> $($f.Name)" -ForegroundColor DarkGray }

# --- 4. Stop + uninstall service ---
$svc = Get-Service -Name cloudflared -ErrorAction SilentlyContinue
if ($svc) {
    if ($svc.Status -eq "Running") {
        Write-Host "[INFO] Arret du service cloudflared..." -ForegroundColor Cyan
        Stop-Service cloudflared -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    Write-Host "[INFO] Desinstallation du service cloudflared..." -ForegroundColor Cyan
    & $CloudflaredExe service uninstall 2>&1 | Out-String | Write-Host -ForegroundColor DarkGray
    Start-Sleep -Seconds 2
} else {
    Write-Host "[INFO] Aucun service cloudflared a desinstaller." -ForegroundColor DarkGray
}

# --- 5. Creer le dossier system ---
$dst = "C:\Windows\System32\config\systemprofile\.cloudflared"
if (-not (Test-Path $dst)) {
    New-Item -ItemType Directory -Path $dst -Force | Out-Null
    Write-Host "[OK] Cree : $dst" -ForegroundColor Green
} else {
    Write-Host "[INFO] Existe deja : $dst" -ForegroundColor DarkGray
}

# --- 6. Copier les fichiers ---
Copy-Item $srcConfig (Join-Path $dst "config.yml") -Force
Write-Host "[OK] Copie config.yml" -ForegroundColor Green

foreach ($f in $srcCredentials) {
    Copy-Item $f.FullName (Join-Path $dst $f.Name) -Force
    Write-Host "[OK] Copie $($f.Name)" -ForegroundColor Green
}

if ($srcCert) {
    Copy-Item $srcCert (Join-Path $dst "cert.pem") -Force
    Write-Host "[OK] Copie cert.pem" -ForegroundColor Green
}

# --- 7. Mettre a jour le path credentials-file dans config.yml ---
$dstConfig = Join-Path $dst "config.yml"
$content = Get-Content $dstConfig -Raw
$srcDirEscaped = [regex]::Escape($SourceDir)

# Remplacer le path source par le path destination si present
if ($content -match $srcDirEscaped) {
    $newContent = $content -replace $srcDirEscaped, $dst.Replace('\', '\\')
    Set-Content -Path $dstConfig -Value $newContent -NoNewline
    Write-Host "[OK] Path credentials-file mis a jour vers $dst" -ForegroundColor Green
} else {
    Write-Host "[INFO] Pas de path absolu vers SourceDir dans config.yml, OK" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "--- Contenu final de $dstConfig ---" -ForegroundColor Cyan
Get-Content $dstConfig | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
Write-Host ""

# --- 8. Reinstaller le service ---
Write-Host "[INFO] Installation du service cloudflared..." -ForegroundColor Cyan
& $CloudflaredExe service install 2>&1 | Out-String | Write-Host -ForegroundColor DarkGray
Start-Sleep -Seconds 3

# --- 9. Demarrer le service ---
$svc = Get-Service -Name cloudflared -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Host "[ERREUR] Service cloudflared toujours absent apres install." -ForegroundColor Red
    exit 1
}
if ($svc.Status -ne "Running") {
    Write-Host "[INFO] Demarrage du service..." -ForegroundColor Cyan
    Start-Service cloudflared
    Start-Sleep -Seconds 5
}
$svc = Get-Service -Name cloudflared
Write-Host "[OK] Service cloudflared : $($svc.Status), StartType $($svc.StartType)" -ForegroundColor Green

# --- 10. Verifier les connecteurs ---
Write-Host ""
Write-Host "Attente 8s pour que le tunnel se connecte aux edges Cloudflare..." -ForegroundColor Cyan
Start-Sleep -Seconds 8
Write-Host ""
Write-Host "--- cloudflared tunnel list ---" -ForegroundColor Cyan
& $CloudflaredExe tunnel list 2>&1 | Out-String | Write-Host

# --- 11. Test endpoint exterieur (optionnel) ---
if ($TestHostname) {
    Write-Host ""
    Write-Host "--- Test https://$TestHostname/ ---" -ForegroundColor Cyan
    try {
        $response = Invoke-WebRequest -Uri "https://$TestHostname/" -UseBasicParsing -TimeoutSec 10 -SkipHttpErrorCheck -MaximumRedirection 0 -ErrorAction SilentlyContinue
        $code = $response.StatusCode
        if ($code -in @(200, 301, 302, 303, 401, 403)) {
            Write-Host "[OK] HTTP $code : le tunnel route correctement !" -ForegroundColor Green
        } elseif ($code -eq 530) {
            Write-Host "[FAIL] HTTP 530 : Cloudflare ne joint toujours pas l'origin." -ForegroundColor Red
            Write-Host "       Verifie : cloudflared tunnel info <name>" -ForegroundColor Yellow
            Write-Host "       et : Get-EventLog -LogName Application -Source cloudflared* -Newest 20" -ForegroundColor Yellow
        } else {
            Write-Host "[?] HTTP $code : a investiguer" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host ""
    Write-Host "[INFO] Pas de TestHostname fourni, test endpoint skip." -ForegroundColor DarkGray
    Write-Host "       Pour tester : .\fix-cloudflare-tunnel.ps1 -TestHostname tautulli.mondomaine.fr" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Termine. Si CONNECTIONS est non vide ci-dessus et que le test a HTTP 200/401/etc.," -ForegroundColor Cyan
Write-Host "le fix est OK. Sinon, regarde les logs :" -ForegroundColor Cyan
Write-Host "  Get-EventLog -LogName Application -Source 'cloudflared*' -Newest 20" -ForegroundColor DarkGray
Write-Host ""
