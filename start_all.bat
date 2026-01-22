@echo off
echo ===================================================
echo   DEMARRAGE COMPLET DU DASHBOARD
echo ===================================================
echo.
echo Ce script lance TOUS les services :
echo  [1] Scraper automatique (toutes les 6h)
echo  [2] API Hardware Monitor (.NET)
echo  [3] Pusher FTP Hardware (temps reel)
echo.
echo Pour arreter : stop_all.bat
echo ===================================================
echo.

cd /d "%~dp0"

:: === VERIFICATIONS ===
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe
    pause
    exit /b 1
)

if not exist ".env" (
    echo [ERREUR] Fichier .env manquant
    echo Copiez .env.example en .env
    pause
    exit /b 1
)

:: === NETTOYAGE DES ANCIENNES INSTANCES ===
echo [INFO] Nettoyage des anciennes instances...
taskkill /F /IM hwMonitor.exe >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *trigger_server*" >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *hw_pusher*" >nul 2>&1
timeout /t 1 /nobreak >nul

:: === RECUPERATION DU TOKEN ===
for /f "delims=" %%i in ('powershell -Command "Get-Content .env | Select-String 'HWMONITOR_TOKEN' | ForEach-Object { $_.ToString().Split('=', 2)[1].Trim().Trim('\"') }"') do set TOKEN=%%i

if "%TOKEN%"=="" (
    echo [ERREUR] HWMONITOR_TOKEN manquant dans .env
    pause
    exit /b 1
)

:: === LANCEMENT DES SERVICES ===

:: 1. Scraper automatique (FastAPI)
echo [1/3] Lancement du Scraper automatique...
start "Scraper Auto" /MIN python trigger_server.py
timeout /t 2 /nobreak >nul

:: 2. API Hardware Monitor (.NET)
echo [2/3] Lancement de hwMonitor...
start "hwMonitor" /MIN /B "hwMonitor\bin\Debug\net8.0\hwMonitor.exe" --urls "http://localhost:5056" --HWMONITOR_TOKEN "%TOKEN%"
timeout /t 3 /nobreak >nul

:: 3. Pusher FTP Hardware
echo [3/3] Lancement du Pusher FTP...
start "Pusher FTP" /MIN python hw_pusher.py

echo.
echo ===================================================
echo   TOUS LES SERVICES SONT DEMARRES !
echo ===================================================
echo.
echo  - Scraper : http://localhost:8888 (6h auto)
echo  - hwMonitor : http://localhost:5056
echo  - Pusher FTP : Actif (2s)
echo.
echo Pour arreter : Lancez stop_all.bat
echo ===================================================
pause
