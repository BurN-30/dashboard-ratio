@echo off
echo Arret du Dashboard en cours...

:: Tue tous les processus Python (le serveur + le pusher)
taskkill /F /IM python.exe /T >nul 2>&1

:: Tue tous les processus Ngrok (le tunnel)
taskkill /F /IM ngrok.exe /T >nul 2>&1

:: Tue les processus .NET (hwMonitor)
taskkill /F /IM dotnet.exe /T >nul 2>&1
taskkill /F /IM hwMonitor.exe /T >nul 2>&1

echo.
echo Tout est eteint.
pause