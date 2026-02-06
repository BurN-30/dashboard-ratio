@echo off
echo ===================================================
echo   Hardware Agent - Dashboard V2
echo ===================================================
echo.

cd /d "%~dp0"

:: Verifier Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH
    pause
    exit /b 1
)

:: Verifier le fichier .env
if not exist ".env" (
    echo [ERREUR] Fichier .env manquant
    echo Copiez .env.example en .env et configurez les valeurs
    pause
    exit /b 1
)

:: Installer les dependances si necessaire
if not exist "venv" (
    echo [SETUP] Creation de l'environnement virtuel...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

:: Lancer l'agent
echo [START] Lancement de l'agent...
python agent.py

pause
