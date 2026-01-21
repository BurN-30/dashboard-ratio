@echo off
title Dashboard AUTOMATIQUE (ALL-IN-ONE)
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

:: --- CHARGEMENT .ENV (Si présent) ---
if exist .env (
    for /f "usebackq tokens=1* delims==" %%A in (".env") do (
        if not "%%A"=="" set "%%A=%%B"
    )
)

:: --- CONFIGURATION ---
:: Token partagé entre l'API .NET et le script Python
:: Les valeurs doivent être définies dans les variables d'environnement ou le fichier .env
if "%HWMONITOR_TOKEN%"=="" (
    echo [ERREUR] HWMONITOR_TOKEN manquant. Verifiez votre fichier .env
    pause
    exit /b 1
)
if "%TRIGGER_TOKEN%"=="" (
    echo [ERREUR] TRIGGER_TOKEN manquant. Verifiez votre fichier .env
    pause
    exit /b 1
)

:: 1. NETTOYAGE (On tue tout ce qui pourrait traîner)
echo [1/5] Nettoyage des anciens processus...
taskkill /F /IM ngrok.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM dotnet.exe >nul 2>&1
taskkill /F /IM hwMonitor.exe >nul 2>&1

:: 2. LANCEMENT DU MONITORING HARDWARE (.NET)
echo [2/5] Lancement API Hardware (.NET)...

:: Detection automatique du chemin du projet (Racine ou Sous-dossier)
set "PROJECT_DIR=hwMonitor"
if exist "Partie Dahboard Ratio\hwMonitor\hwMonitor.csproj" set "PROJECT_DIR=Partie Dahboard Ratio\hwMonitor"

if not exist "%PROJECT_DIR%\hwMonitor.csproj" (
    echo [ERREUR CRITIQUE] Le fichier projet est introuvable dans "%PROJECT_DIR%" !
    echo Veuillez copier le dossier 'hwMonitor' au meme endroit que ce script.
    pause
    exit /b 1
)

:: On lance le projet .NET en arrière-plan. 
start /B "HW Monitor API" dotnet run --project "%PROJECT_DIR%" --urls "http://0.0.0.0:5056"

:: Pause de 5s pour laisser le temps à l'API .NET de démarrer
echo [INFO] Attente demarrage API .NET (5s)...
timeout /t 5 >nul

:: 3. LANCEMENT DU SERVEUR PYTHON (FastAPI) EN ARRIERE-PLAN
echo [3/5] Lancement Serveur Python FastAPI...
start /B "Python FastAPI" python trigger_server.py

:: Pause de 10s pour laisser le temps au serveur Python de démarrer
echo [INFO] Attente demarrage serveur Python (10s)...
timeout /t 10 >nul

:: 4. LANCEMENT DU TUNNEL (Ngrok) - EN DERNIER
echo [4/5] Lancement Ngrok (tunnel vers port 8888)...
if "%NGROK_DOMAIN%"=="" (
    echo [INFO] NGROK_DOMAIN non defini, lancement sans domaine fixe...
    start /B ngrok http 8888 >nul 2>&1
) else (
    start /B ngrok http --domain=%NGROK_DOMAIN% 8888 >nul 2>&1
)

echo.
echo ============================================
echo [5/5] TOUS LES SERVICES SONT DEMARRES !
echo ============================================
echo - API Hardware : http://localhost:5056
echo - API Python : http://localhost:8888
echo - Ngrok Tunnel : Verifiez sur http://localhost:4040
echo.
echo Appuyez sur CTRL+C pour arreter tous les services.
echo ============================================
echo.

:: Garder la fenêtre ouverte (attente infinie)
pause >nul