@echo off
echo ===================================================
echo   DEMARRAGE DU MONITORING (MODE PUSH FTP)
echo ===================================================

cd /d "%~dp0"

:: Nettoyage : Tuer les anciennes instances pour libérer le port 5056
taskkill /F /IM hwMonitor.exe >nul 2>&1

:: 0. Récupérer le token depuis le fichier .env avec PowerShell
for /f "delims=" %%i in ('powershell -Command "Get-Content .env | Select-String 'HWMONITOR_TOKEN' | ForEach-Object { $_.ToString().Split('=', 2)[1].Trim().Trim('\"') }"') do set TOKEN=%%i

if "%TOKEN%"=="" (
    echo [ERREUR] Impossible de lire HWMONITOR_TOKEN dans le fichier .env
    echo Verifiez que la ligne HWMONITOR_TOKEN="votre_token" existe bien.
    pause
    exit /b
)

:: 1. Démarrer le moniteur matériel (C#) en arrière-plan avec le token injecté
echo [1/2] Lancement de hwMonitor...
start /B "" "hwMonitor\bin\Debug\net8.0\hwMonitor.exe" --urls "http://localhost:5056" --HWMONITOR_TOKEN "%TOKEN%" > nul 2>&1

:: Attendre un peu que le serveur démarre
timeout /t 3 /nobreak > nul

:: 2. Démarrer le script Python qui envoie les données au FTP
echo [2/2] Lancement du Pusher FTP...
python hw_pusher.py

pause