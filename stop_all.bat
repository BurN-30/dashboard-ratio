@echo off
echo ===================================================
echo   ARRET DE TOUS LES SERVICES
echo ===================================================

:: Arrêter hwMonitor
taskkill /F /IM hwMonitor.exe 2>nul
if %errorlevel% equ 0 (
    echo [OK] hwMonitor arrete
) else (
    echo [INFO] hwMonitor n'etait pas en cours d'execution
)

:: Arrêter uniquement le script Python hw_pusher.py
for /f "tokens=2" %%a in ('tasklist /v /fo list /fi "imagename eq python.exe" ^| findstr /i "hw_pusher"') do (
    taskkill /F /PID %%a 2>nul
    if %errorlevel% equ 0 (
        echo [OK] hw_pusher.py arrete
    )
)

:: Arrêter trigger_server.py (FastAPI)
for /f "tokens=2" %%a in ('tasklist /v /fo list /fi "imagename eq python.exe" ^| findstr /i "trigger_server"') do (
    taskkill /F /PID %%a 2>nul
    if %errorlevel% equ 0 (
        echo [OK] trigger_server.py arrete
    )
)

:: Arrêter Node.js seulement si c'est le dashboard (port 3000 ou dans ce répertoire)
wmic process where "name='node.exe' and commandline like '%%torrent-dashboard%%'" call terminate 2>nul
if %errorlevel% equ 0 (
    echo [OK] Dashboard Node.js arrete
) else (
    echo [INFO] Dashboard Node.js n'etait pas en cours d'execution
)

echo.
echo Processus specifiques arretes.
pause
