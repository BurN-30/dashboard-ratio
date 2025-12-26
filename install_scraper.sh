#!/bin/bash
# Script d'installation du scraper sur une machine distante (Linux/Mac)

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  🚀 Installation - Torrent Scraper"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    echo "Installation: sudo apt-get install python3 python3-pip"
    exit 1
fi

echo "✅ Python 3 trouvé: $(python3 --version)"
echo ""

# Aller au répertoire du projet
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 Répertoire du projet: $SCRIPT_DIR"
echo ""

# Installer les dépendances Python
echo "📦 Installation des dépendances Python..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "✅ Dépendances installées"
echo ""

# Installer Playwright browsers
echo "🌐 Installation des navigateurs Playwright..."
python3 -m playwright install chromium

echo "✅ Navigateurs installés"
echo ""

# Vérifier le fichier .env
if [ ! -f ".env" ]; then
    echo "⚠️  Fichier .env non trouvé!"
    echo ""
    echo "Créez un fichier .env avec:"
    echo "────────────────────────────────────────────────────────────"
    cat << 'EOF'
# FTP O2Switch
FTP_HOST=REDACTED
FTP_USER=your_username
FTP_PASS=your_password
FTP_DIR=/public_html/dash

# Generation-Free
GF_USER=your_username
GF_PASS=your_password

# TheOldSchool
TOS_USER=your_username
TOS_PASS=your_password

# Sharewood
SW_USER=your_username
SW_PASS=your_password
EOF
    echo "────────────────────────────────────────────────────────────"
    exit 1
else
    echo "✅ Fichier .env trouvé"
fi

echo ""

# Test d'exécution
echo "🧪 Test du scraper..."
if python3 scraper.py; then
    echo "✅ Scraper fonctionne correctement"
    echo ""
    echo "📊 Fichiers générés:"
    ls -lh stats.json history.json 2>/dev/null || echo "Fichiers non trouvés"
else
    echo "❌ Erreur lors de l'exécution du scraper"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ Installation terminée!"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo "📋 Prochaines étapes:"
echo ""
echo "1️⃣  Planifier l'exécution automatique:"
echo "   • Linux/Mac: Ajouter au crontab (crontab -e)"
echo "   • 0 */6 * * * cd $(pwd) && python3 scraper.py >> scraper.log 2>&1"
echo ""
echo "2️⃣  Vérifier l'upload FTP:"
echo "   • Accédez à: https://dash.example.com/stats.json"
echo ""
echo "3️⃣  Monitorer les logs:"
echo "   • tail -f scraper.log"
echo ""
