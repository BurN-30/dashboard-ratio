@echo off
REM Script d'installation du scraper sur Windows

setlocal enabledelayedexpansion

echo.
echo ===============================================================
echo   ^>^> Installation - Torrent Scraper (Windows)
echo ===============================================================
echo.

REM Vérifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python n'est pas installe ou n'est pas dans le PATH
    echo.
    echo Installation: https://www.python.org/downloads/
    echo Assurez-vous de cocher "Add Python to PATH" pendant l'installation
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo OK %PYTHON_VERSION%
echo.

REM Aller au répertoire du script
cd /d "%~dp0"
set SCRIPT_DIR=%cd%

echo Repertoire du projet: %SCRIPT_DIR%
echo.

REM Installer les dépendances Python
echo Telechargement des dependances Python...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo X Erreur lors de l'installation des dependances
    pause
    exit /b 1
)

echo OK Dependances installees
echo.

REM Installer Playwright browsers
echo Telechargement des navigateurs Playwright...
python -m playwright install chromium

if errorlevel 1 (
    echo X Erreur lors de l'installation de Playwright
    pause
    exit /b 1
)

echo OK Navigateurs installes
echo.

REM Vérifier le fichier .env
if not exist ".env" (
    echo X Fichier .env non trouve!
    echo.
    echo Creez un fichier .env avec:
    echo ────────────────────────────────────────────────────────────
    echo # FTP O2Switch
    echo FTP_HOST=pin.o2switch.net
    echo FTP_USER=your_username
    echo FTP_PASS=your_password
    echo FTP_DIR=/public_html/dash
    echo.
    echo # Generation-Free
    echo GF_USER=your_username
    echo GF_PASS=your_password
    echo.
    echo # TheOldSchool
    echo TOS_USER=your_username
    echo TOS_PASS=your_password
    echo.
    echo # Sharewood
    echo SW_USER=your_username
    echo SW_PASS=your_password
    echo ────────────────────────────────────────────────────────────
    pause
    exit /b 1
) else (
    echo OK Fichier .env trouve
)

echo.

REM Test d'exécution
echo Test du scraper...
python scraper.py

if errorlevel 1 (
    echo X Erreur lors de l'execution du scraper
    pause
    exit /b 1
) else (
    echo OK Scraper fonctionne correctement
)

echo.
echo Fichiers generes:
if exist stats.json (
    echo   - stats.json ^(^^!derniere execution^)
)
if exist history.json (
    echo   - history.json ^(^!nombre d'entrees^)
)

echo.
echo ===============================================================
echo   OK Installation terminee!
echo ===============================================================
echo.

echo Prochaines etapes:
echo.
echo 1^) Planifier l'execution automatique:
echo    - Ouvrir "Planificateur de taches" ^(taskschd.msc^)
echo    - Creer une tache qui execute: python scraper.py
echo    - Frequence: Toutes les 6 heures
echo.
echo 2^) Verifier l'upload FTP:
echo    - Accedez a: https://dash.example.com/stats.json
echo.
echo 3^) Monitorer l'execution:
echo    - Ajouter des logs dans le script si necessaire
echo.

pause
