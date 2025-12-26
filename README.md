# 🎯 Torrent Dashboard - Tracker Stats

Une **application web complète** pour monitorer vos statistiques de trackers torrent en temps réel.

```
Scraper automatisé (24h/24) → FTP upload → Dashboard web
```

---

## 📊 Fonctionnalités

✅ **Scraping automatisé** des trackers:
- Generation-Free (UNIT3D)
- TheOldSchool (UNIT3D)
- Sharewood

✅ **Historique complet** avec optimisation intelligent:
- Données récentes: toutes les exécutions
- Anciennes données: une entrée par jour max

✅ **Dashboard web** moderne:
- Interface sombre/clair (theme toggle)
- Graphiques en temps réel
- Statistiques détaillées
- Authentification

✅ **Architecture scalable**:
- Scraper sur machine distante
- Données en FTP
- Site web indépendant

---

## 🏗️ Architecture

### Vue d'ensemble

```
┌──────────────────────────────────────────────────────────────┐
│                    MACHINE DISTANTE (24h/24)                │
│                                                               │
│  ┌─────────────────────────────────┐                        │
│  │   scraper.py                    │                        │
│  │  - Scrape 3 trackers via Playwright                      │
│  │  - Génère stats.json            │                        │
│  │  - Génère history.json          │                        │
│  │  - Upload via FTP               │                        │
│  └─────────────────┬───────────────┘                        │
│                    │ FTP Upload                              │
└────────────────────┼──────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│           O2SWITCH Server (dash.example.com)             │
│                                                               │
│  /public_html/dash/                                          │
│  ├── stats.json       (données actuelles)                   │
│  └── history.json     (historique complet)                  │
└────────────────────┬──────────────────────────────────────────┘
                     │ HTTP GET (API Proxy)
                     ▼
┌──────────────────────────────────────────────────────────────┐
│         Next.js Dashboard (dash.example.com)             │
│                                                               │
│  /api/stats      → Proxy → /stats.json                      │
│  /api/history    → Proxy → /history.json                    │
│                                                               │
│  Frontend:                                                   │
│  ├── Dashboard principal                                    │
│  ├── Graphiques d'historique                               │
│  ├── Détails par tracker                                   │
│  └── Authentification                                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 🚀 Démarrage rapide

### 1️⃣ Machine distante avec scraper

#### Installation (Linux/Mac)
```bash
bash install_scraper.sh
```

#### Installation (Windows)
```cmd
install_scraper.bat
```

#### Configurer `.env`
```env
FTP_HOST=pin.o2switch.net
FTP_USER=sana6906
FTP_PASS=58mD-fXqY-AEJ)
FTP_DIR=/public_html/dash

GF_USER=REDACTED_USER
GF_PASS=REDACTED_PASSWORD

TOS_USER=REDACTED_USER
TOS_PASS=REDACTED_PASSWORD

SW_USER=REDACTED_USER
SW_PASS=***REDACTED***01
```

#### Planifier l'exécution 24h/24

**Linux (Crontab):**
```bash
crontab -e
# Ajouter: 0 */6 * * * cd /home/user/dashboard && python3 scraper.py
```

**Windows (Task Scheduler):**
1. Ouvrir "Planificateur de tâches"
2. Créer une tâche récurrente
3. Action: `C:\Python312\python.exe C:\chemin\scraper.py`

---

### 2️⃣ Déployer le site web

#### Option A: Vercel (Recommandé)
```bash
npm install -g vercel
cd torrent-dashboard
vercel
```

#### Option B: O2Switch / VPS
```bash
cd torrent-dashboard
npm install
npm run build
npm run start
```

---

## 🔧 Développement local

### Prérequis
- Node.js 18+
- Python 3.8+
- npm/yarn

### Installation
```bash
# Cloner le repo
git clone https://github.com/BurN-30/dashboard-ratio.git
cd dashboard-ratio

# Frontend
cd torrent-dashboard
npm install
npm run dev
# Ouvre http://localhost:3000

# Scraper (autre terminal)
cd ..
python3 -m venv venv
source venv/bin/activate  # ou: venv\Scripts\activate (Windows)
pip install -r requirements.txt
python scraper.py
```

---

## 📁 Structure du projet

```
dashboard-ratio/
├── scraper.py              # Script principal de scraping
├── requirements.txt        # Dépendances Python
├── .env                    # Variables d'environnement (à créer)
├── stats.json             # Données actuelles (généré)
├── history.json           # Historique (généré)
├── SETUP_GUIDE.md         # Guide d'installation complet
├── test_architecture.py   # Script de diagnostic
├── install_scraper.sh     # Installation Linux/Mac
├── install_scraper.bat    # Installation Windows
└── torrent-dashboard/     # Application Next.js
    ├── package.json
    ├── next.config.ts
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx           # Dashboard principal
    │   │   ├── api/
    │   │   │   ├── stats/route.ts # Proxy /api/stats
    │   │   │   └── history/route.ts # Proxy /api/history
    │   │   ├── traffic/           # Page détails
    │   │   ├── warnings/          # Page avertissements
    │   │   └── login/             # Authentification
    │   ├── components/            # Composants React
    │   ├── lib/api.ts            # Fonctions fetch
    │   └── types/tracker.ts      # Types TypeScript
    └── public/                   # Assets statiques
```

---

## 🧪 Tests et diagnostic

Vérifier que tout fonctionne:

```bash
python test_architecture.py
```

Affiche:
- ✅ Fichiers locaux
- ✅ Configuration .env
- ✅ Connexion FTP
- ✅ Accès web aux fichiers
- ✅ API Next.js

---

## 📊 Format des données

### `stats.json` (données actuelles)
```json
{
  "Generation-Free": {
    "warnings_active": "0",
    "hit_and_run": "0",
    "ratio": "149.48",
    "real_ratio": "24.39",
    "buffer": "297.96 GiB",
    "vol_upload": "149.48 GiB",
    "vol_download": "1 GiB",
    "count_seed": "624",
    "count_leech": "0",
    "seed_time_total": "1Y 4M 1W 1D 3h 35m 32s",
    "seed_time_avg": "18h 58m 2s",
    "points_bonus": "21918",
    "fl_tokens": "0"
  },
  "TheOldSchool": { ... },
  "Sharewood": { ... },
  "_timestamp": 1703000000
}
```

### `history.json` (historique)
```json
[
  {
    "Generation-Free": { ... },
    "TheOldSchool": { ... },
    "Sharewood": { ... },
    "_timestamp": 1703000000
  },
  { ... },
]
```

---

## 🔒 Sécurité

⚠️ **Considérations importantes:**

1. **Ne pas commiter `.env`** dans Git
2. **Protéger les identifiants** (déjà en .env)
3. **HTTPS obligatoire** (✅ configuré)
4. **Limiter l'accès aux JSON** (optionnel: auth HTTP)
5. **Logs sécurisés** (éviter les mots de passe)

### Amélioration: Protéger les fichiers JSON

Créer `.htaccess` dans `/public_html/dash/`:
```apache
<Files "*.json">
    AuthType Basic
    AuthName "Private"
    AuthUserFile /path/to/.htpasswd
    Require valid-user
</Files>
```

---

## 🐛 Dépannage

| Problème | Solution |
|----------|----------|
| `ModuleNotFoundError: No module named 'playwright'` | `python -m pip install -r requirements.txt` |
| FTP timeout | Vérifier la connexion réseau et les logs |
| Fichiers JSON non à jour | Vérifier le cron/Task Scheduler |
| `https://dash.example.com/stats.json` → 404 | Vérifier les permissions FTP |
| Dashboard affiche "Failed to load data" | Vérifier `/api/stats` dans console (F12) |

---

## 📈 Performance

- **Scraper**: ~30-60s par exécution (selon les trackers)
- **Historique**: Optimisé (30j complets, puis 1/jour)
- **API**: Cache désactivé (`no-store`) pour données fraiches
- **Frontend**: Refresh auto toutes les 5 minutes

---

## 🤝 Contribution

Des améliorations bienvenues!

- Ajouter des trackers
- Optimiser le scraping
- Améliorer l'interface
- Ajouter des graphiques

---

## 📞 Support

Problèmes? Vérifiez:
1. [SETUP_GUIDE.md](SETUP_GUIDE.md) - Guide d'installation détaillé
2. [test_architecture.py](test_architecture.py) - Diagnostic complet
3. Console du navigateur (F12) - Erreurs réseau/API

---

## 📝 License

MIT - Libre d'utilisation et modification

---

**Développé avec ❤️ pour monitorer tes stats torrent**
