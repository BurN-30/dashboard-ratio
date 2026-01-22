@echo off
echo ===================================================
echo   DEMARRAGE DU SERVEUR BACKEND COMPLET
echo ===================================================
echo.
echo Ce script lance :
echo  [1] trigger_server.py (FastAPI + Scraper auto 6h)
echo.
echo Pour arreter : Utiliser stop_all.bat
echo ===================================================
echo.

cd /d "%~dp0"

:: Vérifier si Python est installé
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH
    pause
    exit /b 1
)

:: Vérifier si le fichier .env existe
if not exist ".env" (
    echo [ERREUR] Fichier .env manquant
    echo Copiez .env.example en .env et remplissez vos identifiants
    pause
    exit /b 1
)

:: Lancer le serveur FastAPI (scraper automatique)
echo [OK] Lancement de trigger_server.py...
echo.
echo --> Le scraper tournera automatiquement toutes les 6h
echo --> API disponible sur http://localhost:8888
echo.
python trigger_server.py

pause
