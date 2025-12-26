# 📋 Guide de Configuration - Torrent Dashboard

## Architecture

```
┌─────────────────────┐
│   MACHINE DISTANTE  │
│   (Windows/Linux)   │
│  ┌───────────────┐  │
│  │ scraper.py    │  │ Tourne 24h/24
│  │ + .env        │  │
│  └───────────────┘  │
└──────────┬──────────┘
           │ FTP Upload
           ▼
┌─────────────────────┐
│  O2SWITCH (Server)  │
│ /public_html/dash/  │
│  - stats.json       │
│  - history.json     │
└──────────┬──────────┘
           │ HTTP GET
           ▼
┌─────────────────────┐
│ Next.js Dashboard   │
│ (dash.example) │
│ /api/stats ──────┐  │
│ /api/history ────┤─ Proxy vers server
│                  │  
└─────────────────────┘
           │
           ▼ Affichage
      Frontend UI
```

---

## 1️⃣ Configuration de la MACHINE DISTANTE (avec scraper)

### Étape 1: Installer Python + dépendances

```bash
# Windows
python -m pip install -r requirements.txt
python -m playwright install chromium

# Linux
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

### Étape 2: Créer le fichier `.env`

À la **racine du projet** (même dossier que `scraper.py`):

```env
# FTP O2Switch
FTP_HOST=pin.o2switch.net
FTP_USER=sana6906
FTP_PASS=58mD-fXqY-AEJ)
FTP_DIR=/public_html/dash

# Generation-Free (UNIT3D)
GF_USER=REDACTED_USER
GF_PASS=REDACTED_PASSWORD

# TheOldSchool (UNIT3D)
TOS_USER=REDACTED_USER
TOS_PASS=REDACTED_PASSWORD

# Sharewood
SW_USER=REDACTED_USER
SW_PASS=***REDACTED***01
```

### Étape 3: Tester le scraper

```bash
# Test une exécution
python scraper.py

# Doit créer:
# - stats.json (données actuelles)
# - history.json (historique)
# - Upload via FTP
```

### Étape 4: Programmer l'exécution 24h/24

#### ⏰ Windows (Task Scheduler)

1. Ouvrir "Planificateur de tâches"
2. Créer une tâche basique
   - **Nom:** `TorrentScraper`
   - **Déclencheur:** Quotidien, toutes les 6h
   - **Action:** 
     ```
     Program: C:\Python312\python.exe
     Arguments: C:\chemin\vers\scraper.py
     ```

#### 🐧 Linux (Crontab)

```bash
# Éditer crontab
crontab -e

# Ajouter (chaque 6 heures):
0 */6 * * * cd /home/user/dashboard && python3 scraper.py >> scraper.log 2>&1

# Ou chaque heure:
0 * * * * cd /home/user/dashboard && python3 scraper.py >> scraper.log 2>&1
```

---

## 2️⃣ Configuration du SERVEUR WEB (O2Switch)

### Vérifier l'accès aux fichiers

Les fichiers doivent être **accessibles en HTTP**:

- `https://dash.example.com/stats.json` ✅
- `https://dash.example.com/history.json` ✅

Si NON accessible:
1. Vérifier les permissions FTP
2. Vérifier que le dossier `/public_html/dash/` est **public**

### Optionnel: Compresser les fichiers

Si l'historique devient trop volumineux:

```bash
# Sur le serveur, compresser les anciens fichiers
gzip history.json
# Renommer en history.json.gz
```

---

## 3️⃣ Déployer le SITE NEXT.JS

### Options de déploiement:

#### Option A: Vercel (Recommandé - gratuit)
```bash
npm install -g vercel
vercel
# Puis configurer le domaine dash.example.com
```

#### Option B: O2Switch (Shared Hosting)
```bash
# Build
cd torrent-dashboard
npm run build
npm run start

# Sur O2Switch, utiliser Node.js si disponible
# Ou déployer via FTP les fichiers statiques de .next/
```

#### Option C: VPS Personnel
```bash
# SSH vers ton serveur
ssh user@dash.example.com

# Cloner et déployer
git clone https://github.com/BurN-30/dashboard-ratio.git
cd dashboard-ratio/torrent-dashboard
npm install
npm run build
pm2 start npm --name "dashboard" -- start
```

---

## 4️⃣ Variables d'Environnement du Site

Créer `.env.local` dans `torrent-dashboard/`:

```env
# Pas nécessaire pour le moment (API en interne)
# Les identifiants du scraper REST SÉCURISÉS sur la machine distante
```

---

## ✅ Checklist de Vérification

- [ ] Scraper fonctionne en local: `python scraper.py`
- [ ] Fichiers JSON générés: `stats.json`, `history.json`
- [ ] FTP upload réussit
- [ ] `https://dash.example.com/stats.json` accessible
- [ ] `https://dash.example.com/history.json` accessible
- [ ] Site Next.js déployé: `https://dash.example.com/`
- [ ] API proxy fonctionne: `https://dash.example.com/api/stats`
- [ ] Dashboard affiche les données
- [ ] Scraper planifié 24h/24

---

## 🔒 Sécurité - À améliorer

⚠️ **AVANT PRODUCTION:**

1. **Mettre les identifiants en variables d'environnement** ✅ (déjà fait)
2. **Protéger les fichiers JSON** - Ajouter une authentification HTTP
3. **Utiliser HTTPS partout** ✅
4. **Limiter l'accès aux fichiers JSON** au bot scraper uniquement

### Amélioration: Protéger les JSON avec mot de passe

```python
# scraper.py - Ajouter l'authentification
FTP_PASS_HASH = os.getenv("FTP_PASS_HASH")  # Générer avec htpasswd

# O2Switch .htaccess
<Files "*.json">
    AuthType Basic
    AuthName "Stats"
    AuthUserFile /path/to/.htpasswd
    Require valid-user
</Files>
```

---

## 📞 Troubleshooting

| Problème | Solution |
|----------|----------|
| `playwright not found` | `python -m playwright install chromium` |
| FTP timeout | Vérifier l'IP, firewall |
| Fichiers JSON non à jour | Vérifier le cron/Task Scheduler |
| API retourne 404 | Vérifier `https://dash.example.com/stats.json` |
| Dashboard ne charge pas | Vérifier la console (F12), erreurs réseau |

