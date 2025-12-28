@echo off
title Dashboard AUTOMATIQUE (ALL-IN-ONE)
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

:: --- CONFIGURATION ---
:: Token partagé entre l'API .NET et le script Python
set HWMONITOR_TOKEN=301101230669
set TRIGGER_TOKEN=301101230669

:: 1. NETTOYAGE (On tue tout ce qui pourrait traîner)
echo [1/5] Nettoyage des anciens processus...
taskkill /F /IM ngrok.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM dotnet.exe >nul 2>&1
taskkill /F /IM hwMonitor.exe >nul 2>&1

:: 2. LANCEMENT DU TUNNEL (Ngrok)
echo [2/5] Lancement Ngrok...
start /B ngrok http --domain=submedial-bloodlike-sarah.ngrok-free.dev 8000 >nul 2>&1

:: 3. LANCEMENT DU MONITORING HARDWARE (.NET)
echo [3/5] Lancement API Hardware (.NET)...
:: On lance le projet .NET en arrière-plan. 
:: Note : Au premier lancement, cela peut prendre du temps (compilation).
start /B "HW Monitor API" dotnet run --project "hwMonitor" --urls "http://0.0.0.0:5056"

:: Pause de 10s pour laisser le temps à l'API .NET de démarrer
timeout /t 10 >nul

:: 4. LANCEMENT DU PUSHER FTP (Python)
echo [4/5] Lancement Pusher FTP (Hardware)...
start /B "HW Pusher" python "hw_pusher.py"

:: 5. LANCEMENT DU SERVEUR PRINCIPAL (Trigger Scraping)
echo [5/5] Lancement Serveur Trigger (Boucle)...
:boucle
:: Le serveur trigger reste au premier plan pour garder la fenêtre ouverte
python trigger_server.py

:: Si le serveur trigger plante, on attend 5s et on relance
echo [!] Le serveur trigger a crashe. Redemarrage dans 5s...
timeout /t 5 >nul
goto boucle