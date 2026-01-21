# 🎬 Torrent Dashboard

Un dashboard personnel pour suivre vos stats de trackers privés en temps réel. Parce que jongler entre 3 trackers différents pour voir ses ratios, c'est relou.

> ⚠️ **Work In Progress** : Ce projet est fonctionnel mais en développement actif. Des bugs peuvent survenir, et certaines features sont encore en cours d'implémentation. N'hésitez pas à ouvrir une issue si vous rencontrez un problème !

![Dashboard Preview](docs/screenshots/dashboard-preview.png)
*Vue d'ensemble du dashboard avec les stats des 3 trackers*

---

## 💡 Ce que ça fait

Le projet se compose de trois parties qui bossent ensemble :

**1. Le Scraper Python** 🕷️  
Se connecte à vos trackers (Generation-Free, TheOldSchool, Sharewood), récupère vos stats, et les balance en JSON sur votre hébergement FTP. Tourne en arrière-plan toutes les 6h.

**2. Le Monitoring Hardware** 💻  
Une API .NET qui surveille votre CPU, GPU, RAM, disques en temps réel. Histoire de voir si votre machine tient le coup avec tous ces torrents qui tournent.

**3. Le Dashboard Web** 📊  
Une appli Next.js qui affiche tout ça proprement : graphiques d'évolution, stats de ratio, warnings, et monitoring hardware. Accessible de n'importe où.

![Architecture Diagram](docs/screenshots/architecture.png)
*Schéma de l'architecture : PC → FTP/Ngrok → Vercel → Dashboard Web*

---

## 🤔 Pourquoi utiliser Vercel ET un hébergement FTP ?

**Question légitime !** Voici pourquoi cette architecture est nécessaire :

### Le problème : CORS (Cross-Origin Resource Sharing)

Si vous essayez d'accéder directement à vos fichiers JSON depuis le navigateur :

```javascript
// ❌ NE MARCHE PAS (bloqué par CORS)
fetch('https://votresite.com/dash/stats.json')
```

**Les navigateurs bloquent par défaut les requêtes entre différents domaines** pour des raisons de sécurité.

### La solution : Vercel comme proxy serveur

Vercel héberge votre dashboard Next.js et ses **routes API côté serveur** :

```javascript
// ✅ FONCTIONNE
// Le navigateur appelle Vercel
fetch('/api/stats')
  ↓
// Vercel (serveur) fetch votre FTP
fetch('https://votresite.com/dash/stats.json')
  ↓
// Retourne les données au navigateur (pas de CORS !)
```

### Les avantages de Vercel

1. **Contourne CORS** → Les routes API sont côté serveur, pas de blocage
2. **Dashboard 24/7** → Même si votre PC est éteint, le site reste accessible
3. **HTTPS gratuit** → Certificat SSL automatique
4. **Déploiement automatique** → `git push` → site mis à jour en 2 minutes
5. **CDN global** → Chargement ultra-rapide partout dans le monde
6. **Sécurité** → Vos identifiants FTP restent côté serveur (variables d'env)

### Répartition des rôles

```
FTP (O2Switch)         → Stockage des données (stats.json, history.json)
Vercel (Next.js)       → Interface web + Proxy CORS + HTTPS
Ngrok                  → Tunnel pour le monitoring hardware en temps réel
Votre PC               → Scraper + API hardware (quand allumé)
```

**Sans Vercel**, vous devriez :
- Configurer CORS sur votre hébergement (pas toujours possible)
- Exposer votre PC directement sur Internet (dangereux)
- Gérer manuellement les certificats SSL
- Maintenir un serveur web 24/7

**Avec Vercel** : Push sur GitHub → Tout est géré automatiquement ! 🚀

---

## 📋 Prérequis

Avant de commencer, assurez-vous d'avoir :

### Obligatoire
- **Python 3.8 ou supérieur** ([Télécharger](https://www.python.org/downloads/))
- **Node.js 18+ et npm** ([Télécharger](https://nodejs.org/))
- **.NET 8.0 SDK** ([Télécharger](https://dotnet.microsoft.com/download/dotnet/8.0))
- **Un compte sur 3 trackers** : Generation-Free, TheOldSchool, Sharewood
- **Un hébergement web avec FTP** (ex: O2Switch, OVH, Hostinger...) pour stocker les JSON
- **Un compte ngrok** gratuit ([S'inscrire](https://ngrok.com/)) pour exposer l'API hardware
- **Un compte GitHub** (gratuit) pour héberger le code
- **Un compte Vercel** (gratuit) pour déployer le dashboard ([S'inscrire](https://vercel.com/))

### Optionnel mais recommandé
- **Git** pour cloner le repo
- **Windows 10/11** (le script `.bat` est pour Windows, mais adaptable sur Linux/Mac)

---

## 🚀 Installation pas à pas

### Étape 1 : Cloner le projet

```bash
git clone https://github.com/votre-username/torrent-dashboard.git
cd torrent-dashboard
```

### Étape 2 : Backend Python

**Installation des dépendances :**
```bash
pip install -r requirements.txt
python -m playwright install chromium
```

> ⚠️ **Note** : L'installation de Playwright peut prendre 2-3 minutes, c'est normal (télécharge Chromium).

**Configuration :**
```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer avec vos vrais identifiants
notepad .env  # ou nano .env sur Linux/Mac
```

> 📝 **Important** : Le fichier `.env.example` contient toutes les variables nécessaires avec des explications. Prenez le temps de bien le lire avant de le remplir.

**Variables à remplir dans `.env` :**
```bash
# === Vos identifiants trackers ===
GF_USER=votre_username              # Votre login Generation-Free
GF_PASS=votre_password              # Votre mot de passe
GF_USERNAME=votre_username          # Même chose (pour l'URL de profil)

TOS_USER=votre_username             # TheOldSchool
TOS_PASS=votre_password
TOS_USERNAME=votre_username

SW_USER=votre_username              # Sharewood
SW_PASS=votre_password
SW_USERNAME=votre_username.12345    # Format: username.ID (visible dans l'URL de votre profil)

# === Hébergement FTP ===
FTP_HOST=REDACTED    # Adresse FTP de votre hébergeur
FTP_USER=REDACTED             # Login FTP
FTP_PASS=REDACTED             # Mot de passe FTP
FTP_DIR=/public_html/dash           # Dossier où stocker les JSON (créez-le si besoin)

# === Sécurité ===
TRIGGER_TOKEN=generez_un_token_aleatoire_ici    # Ex: openssl rand -hex 32
HWMONITOR_TOKEN=meme_token_ou_different         # Peut être identique

# === Ngrok (après création de votre tunnel) ===
NGROK_DOMAIN=votre-subdomain.ngrok-free.app     # Votre domaine ngrok fixe (optionnel)
DASHBOARD_DOMAIN=https://dash.votre-site.com    # URL de votre dashboard Vercel
```

![Config File Example](docs/screenshots/env-config.png)
*Exemple de fichier .env correctement rempli (avec des fausses valeurs évidemment)*

**Test du scraper :**
```bash
python scraper.py
```

Si tout est bon, vous verrez :
```
--- 🕷️ Démarrage du scraping ---
-> Traitement de : Generation-Free
   ✅ OK
-> Traitement de : TheOldSchool
   ✅ OK
-> Traitement de : Sharewood
   ✅ OK

💾 Fichier stats.json généré en local.
💾 Fichier history.json mis à jour (1 entrées).
```

![Scraper Success](docs/screenshots/scraper-success.png)
*Résultat d'un scraping réussi*

### Étape 3 : API Hardware (.NET)

**Vérifier l'installation .NET :**
```bash
dotnet --version
# Doit afficher : 8.0.x ou supérieur
```

**Tester l'API :**
```bash
cd hwMonitor
dotnet run
```

L'API démarre sur `http://localhost:5056`. Testez avec :
```bash
curl http://localhost:5056/api/health
```

> ⚠️ **Important** : L'API doit être lancée **en mode Administrateur** pour accéder aux capteurs hardware.

### Étape 4 : Configurer Ngrok

**Créer un tunnel :**
```bash
# Connexion (première fois uniquement)
ngrok authtoken VOTRE_TOKEN_NGROK

# Lancer le tunnel
ngrok http 8888
```

Copiez l'URL affichée (ex: `https://abc123.ngrok-free.app`) et mettez-la dans votre `.env` → `NGROK_DOMAIN`

> 💡 **Astuce** : Avec un compte gratuit, l'URL change à chaque redémarrage. Prenez un domaine fixe (payant ~5$/mois) ou mettez à jour `.env` à chaque fois.

![Ngrok Running](docs/screenshots/ngrok-tunnel.png)
*Ngrok en cours d'exécution avec votre tunnel actif*

### Étape 5 : Lancer le backend complet (Windows)

**Méthode simple :**
```bash
start_server.bat
```

Ce script lance automatiquement :
1. L'API Hardware (.NET)
2. Le serveur FastAPI (Python)
3. Ngrok (tunnel)

![Backend Running](docs/screenshots/backend-all-running.png)
*Tous les services backend démarrés*

**Pour arrêter tout :**
```bash
stop_server.bat
```

### Étape 6 : Frontend Next.js (Local)

**Installation :**
```bash
cd torrent-dashboard
npm install
```

**Configuration :**
```bash
cp .env.local.example .env.local
notepad .env.local  # Éditer le fichier
```

> 📝 **Important** : Le fichier `.env.local.example` contient toutes les variables nécessaires pour le frontend. Copiez-le en `.env.local` et remplissez vos vraies valeurs.

**Variables dans `torrent-dashboard/.env.local` :**
```bash
ADMIN_PASSWORD=votre_mot_de_passe_admin         # Pour accéder à /login
JSON_BASE_URL=https://votre-site.com/dash       # Où sont hébergés vos JSON (FTP)
NEXT_PUBLIC_NGROK_URL=https://abc123.ngrok-free.app   # URL de votre tunnel ngrok
NGROK_URL=https://abc123.ngrok-free.app         # Même URL (pour les routes API)
```

**Lancer en dev :**
```bash
npm run dev
```

Ouvrez http://localhost:3000 → Vous devriez voir votre dashboard ! 🎉

![Dashboard Running Locally](docs/screenshots/dashboard-local.png)
*Dashboard tournant en local (mode développement)*

### Étape 7 : Déployer sur Vercel (Production)

**Préparer le repository GitHub :**

1. **Créer un repo sur GitHub** (public ou privé)
2. **Pusher votre code** :
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/votre-username/torrent-dashboard.git
   git push -u origin main
   ```

> ⚠️ **Vérification importante** : Assurez-vous que les fichiers `.env` et `.env.local` ne sont **PAS** pushés (ils sont dans `.gitignore`).

**Déployer sur Vercel :**

1. Créer un compte sur [vercel.com](https://vercel.com/)
2. Cliquer sur **"New Project"**
3. Importer votre repo GitHub
4. **Important** : Dans les paramètres du projet :
   - **Root Directory** : `torrent-dashboard` (car le frontend est dans ce dossier)
   - **Framework Preset** : Next.js (détecté automatiquement)
5. Ajouter les **Environment Variables** :
   ```
   ADMIN_PASSWORD=votre_mot_de_passe
   JSON_BASE_URL=https://votresite.com/dash
   NEXT_PUBLIC_NGROK_URL=https://votre-tunnel.ngrok-free.app
   NGROK_URL=https://votre-tunnel.ngrok-free.app
   ```
6. Cliquer sur **Deploy** 🚀

![Vercel Config](docs/screenshots/vercel-env-vars.png)
*Configuration des variables d'environnement sur Vercel*

**Votre dashboard sera accessible sur** : `https://votre-projet.vercel.app`

Vous pouvez ensuite connecter votre domaine personnalisé (ex: `dash.example.com`) dans les paramètres Vercel.

---

## 📁 Architecture

```
.
├── scraper.py              # Scrape les trackers toutes les 6h
├── trigger_server.py       # API FastAPI (endpoints + proxy hardware)
├── start_server.bat        # Lance tout d'un coup (Windows)
├── stop_server.bat         # Arrête tout
├── .env                    # ⚠️ VOS IDENTIFIANTS (ne pas commit !)
├── .env.example            # 📄 Fichier exemple à copier en .env
│
├── hwMonitor/             # API C# monitoring hardware
│   ├── Program.cs         # Point d'entrée
│   └── Services/          # Logique de récupération stats
│
└── torrent-dashboard/     # Frontend Next.js
    ├── .env.local         # ⚠️ Config frontend (ne pas commit !)
    ├── .env.local.example # 📄 Fichier exemple à copier en .env.local
    ├── src/app/
    │   ├── page.tsx       # Page d'accueil (stats overview)
    │   ├── traffic/       # 📊 Graphiques trafic
    │   ├── warnings/      # ⚠️ Suivi warnings/H&R
    │   └── api/           # Routes API (proxy vers FTP/Ngrok)
    └── src/components/    # Composants réutilisables
```

---

## 🎯 Fonctionnalités

### Page principale
![Main Dashboard](docs/screenshots/dashboard-main.png)

- ✅ Vue d'ensemble des 3 trackers
- ✅ Ratios, buffer, points bonus
- ✅ Warnings et Hit'n'Run actifs
- ✅ Nombre de torrents en seed/leech
- ✅ Mise à jour automatique toutes les 30 secondes

### Page Trafic
![Traffic Charts](docs/screenshots/dashboard-traffic.png)

- ✅ Graphiques d'évolution sur 30 jours
- ✅ Upload / Download / Ratio / Buffer
- ✅ Comparaison entre trackers
- ✅ Export CSV possible

### Page Warnings
![Warnings Page](docs/screenshots/dashboard-warnings.png)

- ✅ Suivi des warnings actifs
- ✅ Historique des Hit'n'Run
- ✅ Alertes si seuil critique

### Monitoring Hardware
![Hardware Monitor](docs/screenshots/hardware-stats.png)

- ✅ CPU : charge, température, fréquence
- ✅ GPU : charge, température, VRAM, consommation
- ✅ RAM : utilisée / totale
- ✅ Disques : espace, température
- ✅ Réseau : upload/download en temps réel

---

## 🛠️ Utilisation quotidienne

### Lancement automatique au démarrage (Windows)

1. Ouvrir le **Planificateur de tâches**
2. Créer une tâche → **Au démarrage de Windows**
3. Action : Lancer `start_server.bat`
4. Paramètres : Cocher "Exécuter même si l'utilisateur n'est pas connecté"

### Lancement manuel

```bash
# Tout lancer d'un coup
start_server.bat

# Ou étape par étape
python trigger_server.py     # API Python seule
python scraper.py            # Scraper manuel (test)
cd hwMonitor && dotnet run   # API hardware seule
```

### Commandes utiles

```bash
# Backend
python scraper.py           # Scraper manuel
stop_server.bat             # Tout arrêter

# Frontend
npm run dev                 # Dev local
npm run build               # Build production
npm run start               # Servir le build
```

---

## 🔐 Sécurité

### Fichiers à ne JAMAIS committer

✅ Déjà dans `.gitignore` :
- `.env` (identifiants backend) → Copie de `.env.example`
- `stats.json`, `history.json`, `hardware.json` (données générées)
- `torrent-dashboard/.env.local` (config frontend) → Copie de `.env.local.example`

### Fichiers exemples à conserver

✅ Ces fichiers DOIVENT être commités (ils sont génériques) :
- `.env.example` → Template pour le backend
- `torrent-dashboard/.env.local.example` → Template pour le frontend

### Protections recommandées

1. **Tokens forts** : Générez des tokens aléatoires avec `openssl rand -hex 32`
2. **HTTPS partout** : Vercel le fait automatiquement
3. **Protéger le dossier FTP** : Ajoutez un `.htaccess` avec Basic Auth
4. **Mot de passe admin robuste** : Pour la page `/login`

Exemple `.htaccess` pour votre dossier FTP `/dash` :
```apache
AuthType Basic
AuthName "Dashboard Stats"
AuthUserFile /home/votre_user/.htpasswd
Require valid-user
```

---

## 🐛 Problèmes courants

### "Dernière mise à jour" ne se met pas à jour
**Cause** : L'API `/api/stats` ne trouve pas les JSON  
**Solution** : 
1. Vérifiez que `JSON_BASE_URL` est correct dans `.env.local` (Vercel)
2. Testez l'URL directement : `https://votre-site.com/dash/stats.json`
3. Regardez les logs Vercel pour voir l'erreur exacte

### Erreur 401 sur l'API hardware
**Cause** : Token incorrect ou API .NET non démarrée  
**Solution** :
1. Vérifiez que `HWMONITOR_TOKEN` est identique dans `.env`
2. Lancez l'API .NET **en mode Administrateur**
3. Testez `http://localhost:5056/api/health`

### Le scraper ne se connecte pas aux trackers
**Cause** : Identifiants incorrects ou Playwright non installé  
**Solution** :
1. Vérifiez vos identifiants dans `.env`
2. Réinstallez Playwright : `python -m playwright install chromium`
3. Testez manuellement : `python scraper.py` et regardez les erreurs

### "stats.json" introuvable sur le FTP
**Cause** : Le scraper n'upload pas ou mauvais chemin  
**Solution** :
1. Vérifiez `FTP_HOST`, `FTP_USER`, `FTP_PASS`, `FTP_DIR` dans `.env`
2. Créez le dossier `/dash` sur votre hébergement si besoin
3. Testez un upload manuel via Filezilla pour vérifier les accès

### Ngrok : "tunnel not found"
**Cause** : Le domaine a changé (gratuit) ou tunnel éteint  
**Solution** :
1. Relancez ngrok : `ngrok http 8888`
2. Copiez la nouvelle URL et mettez à jour `.env` → `NGROK_DOMAIN`
3. **Important** : Mettez aussi à jour les variables d'env sur Vercel !

### Le dashboard Vercel affiche "Configuration Error"
**Cause** : Variables d'environnement manquantes sur Vercel  
**Solution** :
1. Allez sur Vercel → Votre projet → Settings → Environment Variables
2. Vérifiez que `JSON_BASE_URL` et `NGROK_URL` sont bien définies
3. Redéployez le projet (Deployments → Redeploy)

---

## 📝 FAQ

**Q : Ça coûte combien ?**  
R : Gratuit si vous avez déjà un hébergement web. Ngrok gratuit suffit (mais l'URL change). Vercel est gratuit. GitHub est gratuit. Seul coût possible : domaine ngrok fixe (~5$/mois).

**Q : Ça marche sur Mac/Linux ?**  
R : Oui ! Il faut juste adapter `start_server.bat` en shell script `.sh`. Le reste est identique.

**Q : Combien de fois le scraper se lance ?**  
R : Toutes les 6h automatiquement. Modifiable dans `trigger_server.py` → `SCRAPE_INTERVAL_HOURS`.

**Q : Peut-on ajouter d'autres trackers ?**  
R : Oui ! Éditez `scraper.py` et ajoutez votre tracker dans la liste `SITES`. S'il utilise UNIT3D, ça devrait marcher direct.

**Q : C'est sécurisé ?**  
R : Tant que vous ne commitez pas vos `.env` sur GitHub, oui. Les données JSON sont sur votre FTP (que vous contrôlez). Ajoutez un `.htaccess` si vous voulez plus de protection.

**Q : Le dashboard consomme beaucoup de ressources ?**  
R : Non, très léger :
- Scraper : 1-2 min toutes les 6h
- API Hardware : ~50 Mo RAM
- Frontend : hébergé sur Vercel (gratuit, ultra rapide)

**Q : Mon PC doit être allumé 24/7 ?**  
R : Non ! Seulement pour le **monitoring hardware en temps réel**. Les stats torrents restent accessibles même PC éteint (elles sont sur FTP).

---

## 🤝 Contribution

C'est un projet perso, mais si vous voulez :
- Ajouter d'autres trackers
- Améliorer les graphiques
- Proposer des features

→ Forkez et faites une PR, je suis ouvert ! 🙂

---

## 📄 Licence

MIT - Faites-en ce que vous voulez, modifiez, distribuez, pas de contraintes.

---

## 📸 Screenshots

Pour compléter la documentation, ajoutez quelques captures du dashboard dans `docs/screenshots/` :

1. **`dashboard-preview.png`** ⭐ → Vue d'ensemble de la page principale
2. **`dashboard-traffic.png`** → Page `/traffic` avec les graphiques
3. **`dashboard-warnings.png`** → Page `/warnings` avec les alertes
4. **`hardware-stats.png`** → Page monitoring hardware (optionnel)

**Structure à créer :**
```bash
mkdir docs
mkdir docs\screenshots
# Puis placez vos images PNG dans docs/screenshots/
```

> 💡 **Astuce** : Utilisez des captures en plein écran, en mode sombre de préférence (c'est plus joli sur GitHub). Si vous n'avez pas encore de données, un scraping manuel génère du contenu immédiatement.

---

*Fait avec ❤️ et beaucoup de café pour éviter de se faire ban des trackers*

**Besoin d'aide ?** Ouvrez une issue sur GitHub ou regardez les logs d'erreur dans la console. 90% des problèmes viennent d'une variable mal configurée dans les `.env` ou sur Vercel 😉