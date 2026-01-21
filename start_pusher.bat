@echo off
echo ===================================================
echo   DEMARRAGE DU MONITORING (MODE PUSH FTP)
echo ===================================================

cd /d "%~dp0"

:: 1. Démarrer le moniteur matériel (C#) en arrière-plan
echo [1/2] Lancement de hwMonitor...
start /B "" "hwMonitor\bin\Debug\net8.0\hwMonitor.exe" --urls "http://localhost:5056" > nul 2>&1

:: Attendre un peu que le serveur démarre
timeout /t 3 /nobreak > nul

:: 2. Démarrer le script Python qui envoie les données au FTP
echo [2/2] Lancement du Pusher FTP...
python hw_pusher.py

pause