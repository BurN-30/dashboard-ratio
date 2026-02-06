@echo off
echo ===================================================
echo   DEMARRAGE COMPLET DU DASHBOARD
echo ===================================================
echo.

cd /d "%~dp0"

:: === VERIFICATIONS ===
echo [CHECK] Verification de Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH
    pause
    exit /b 1
)
echo [OK] Python detecte

echo [CHECK] Verification du fichier .env...
if not exist ".env" (
    echo [ERREUR] Fichier .env manquant
    echo Copiez .env.example en .env et remplissez vos identifiants
    pause
    exit /b 1
)
echo [OK] Fichier .env trouve

echo [CHECK] Verification de l'executable hwMonitor...
if not exist "hwMonitor\bin\Debug\net8.0\hwMonitor.exe" (
    echo [ERREUR] hwMonitor.exe introuvable
    echo Vous devez compiler le projet .NET :
    echo   cd hwMonitor
    echo   dotnet build
    pause
    exit /b 1
)
echo [OK] hwMonitor.exe trouve

:: === NETTOYAGE DES ANCIENNES INSTANCES ===
echo.
echo [CLEAN] Nettoyage des anciennes instances...
taskkill /F /IM hwMonitor.exe >nul 2>&1
for /f "tokens=2" %%a in ('tasklist /v /fo list /fi "imagename eq python.exe" ^| findstr /i "trigger_server"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=2" %%a in ('tasklist /v /fo list /fi "imagename eq python.exe" ^| findstr /i "hw_pusher"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 1 /nobreak >nul
echo [OK] Nettoyage termine

:: === RECUPERATION DU TOKEN ===
echo.
echo [CONFIG] Lecture du token depuis .env...
for /f "delims=" %%i in ('powershell -Command "Get-Content .env | Select-String 'HWMONITOR_TOKEN' | ForEach-Object { $_.ToString().Split('=', 2)[1].Trim().Trim('\"') }"') do set TOKEN=%%i

if "%TOKEN%"=="" (
    echo [ERREUR] HWMONITOR_TOKEN manquant ou vide dans .env
    echo Ajoutez cette ligne dans votre .env :
    echo   HWMONITOR_TOKEN="votre_token_ici"
    pause
    exit /b 1
)
echo [OK] Token recupere : %TOKEN:~0,10%...

:: === LANCEMENT DES SERVICES ===
echo.
echo ===================================================
echo   LANCEMENT DES SERVICES
echo ===================================================
echo.

:: 1. Scraper automatique (FastAPI)
echo [1/3] Lancement du Scraper automatique (FastAPI)...
start "Dashboard - Scraper Auto" /MIN cmd /c "python trigger_server.py || pause"
timeout /t 3 /nobreak >nul
echo [OK] Scraper lance

:: 2. API Hardware Monitor (.NET)
echo [2/3] Lancement de hwMonitor API (.NET)...
start "Dashboard - hwMonitor" /MIN cmd /c "hwMonitor\bin\Debug\net8.0\hwMonitor.exe --urls http://localhost:5056 --HWMONITOR_TOKEN %TOKEN% || pause"
timeout /t 3 /nobreak >nul
echo [OK] hwMonitor lance

:: 3. Pusher FTP Hardware
echo [3/3] Lancement du Pusher FTP (Hardware vers FTP)...
start "Dashboard - Pusher FTP" /MIN cmd /c "python hw_pusher.py || pause"
timeout /t 2 /nobreak >nul
echo [OK] Pusher lance

:: === VERIFICATION QUE LES SERVICES TOURNENT ===
echo.
echo [VERIFY] Verification des services (attente 5 secondes)...
timeout /t 5 /nobreak >nul

tasklist /FI "IMAGENAME eq hwMonitor.exe" 2>NUL | find /I /N "hwMonitor.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] hwMonitor.exe est actif
) else (
    echo [WARNING] hwMonitor.exe ne semble pas actif
)

tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I /N "python.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] Python est actif
) else (
    echo [WARNING] Aucun script Python detecte
)

echo.
echo ===================================================
echo   TOUS LES SERVICES SONT DEMARRES !
echo ===================================================
echo.
echo  Services disponibles :
echo   - Scraper API  : http://localhost:8888
echo   - hwMonitor    : http://localhost:5056
echo   - Pusher FTP   : Actif (toutes les 2s)
echo.
echo  Si erreur 502 sur le site :
echo   1. Verifiez les fenetres minimisees (barre des taches)
echo   2. Regardez les logs d'erreur dans ces fenetres
echo   3. Testez manuellement : python trigger_server.py
echo.
echo  Pour arreter : stop_all.bat
echo ===================================================
echo.
pause
