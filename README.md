# TrackBoard

Dashboard personnel pour suivre les stats de trackers torrent privés et monitorer son hardware en temps réel.

<p align="center">
  <img src="docs/screenshot-tracker-dark.svg" alt="Statistiques Trackers" width="700" />
</p>

<p align="center">
  <img src="docs/screenshot-hardware-dark.svg" alt="Monitoring Hardware" width="700" />
</p>

<p align="center">
  <a href="https://trackboard-burn-30-nathan-saccols-projects.vercel.app"><strong>Voir la demo en ligne</strong></a>
</p>

## Fonctionnalités

**Statistiques Trackers**
- Ratio, buffer, upload/download, bonus points par tracker
- Graphiques d'historique (ratio, buffer) sur 30 jours
- Support UNIT3D, Sharewood et scrapers custom
- Liens rapides vers les boutiques bonus
- Scraping automatique à intervalles configurables

**Monitoring Hardware**
- CPU : charge, température, puissance, fréquence, ventilateur, charge par coeur
- GPU : charge, température, VRAM, puissance, ventilateur
- RAM : utilisation en temps réel
- Stockage : espace disque, températures HDD/NVMe
- Réseau : upload/download en temps réel
- Uptime système

## Architecture

```
[PC Local]                       [VPS]
hw-agent ──WebSocket──> Nginx ──> Backend (FastAPI)
                                      ├── PostgreSQL
                                      ├── Scrapers (Playwright)
                                      └── REST API + WebSocket
                                   Nginx ──> Frontend (Next.js)
```

| Composant | Stack |
|-----------|-------|
| **Backend** | FastAPI, async SQLAlchemy, JWT, WebSocket |
| **Frontend** | Next.js, Tailwind CSS, ApexCharts, dark/light mode |
| **Scrapers** | Playwright headless (Chromium), UNIT3D + Sharewood |
| **HW Agent** | Python (psutil, nvidia-smi, LibreHardwareMonitor WMI) |
| **Infra** | Docker Compose, Nginx reverse proxy, Let's Encrypt SSL |

## Prérequis

- **Serveur/VPS** avec Docker et Docker Compose
- **Nginx** en reverse proxy (SSL via Let's Encrypt)
- **Python 3.10+** sur le PC local (pour hw-agent)
- **LibreHardwareMonitor** actif sur le PC (pour les températures CPU/disques)
- Comptes sur les trackers privés à monitorer

## Installation

### 1. Cloner

```bash
git clone https://github.com/BurN-30/dashboard-ratio.git
cd dashboard-ratio/dashboard-v2
```

### 2. Configurer

```bash
cp .env.example .env
# Editer .env avec vos identifiants
```

Variables principales :

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | URL PostgreSQL |
| `JWT_SECRET` | Clé secrète JWT (`openssl rand -hex 32`) |
| `ADMIN_PASSWORD` | Mot de passe admin du dashboard |
| `DOMAIN` | Votre domaine (ex: `dashboard.example.com`) |
| `HW_AGENT_TOKEN` | Token de l'agent hardware (`openssl rand -hex 16`) |
| `TRACKER_USERNAME` | Pseudo tracker (pour les liens boutique) |
| `SW_USER/PASS` | Identifiants Sharewood |
| `GF_USER/PASS` | Identifiants Generation-Free |
| `TOS_USER/PASS` | Identifiants TheOldSchool |

### 3. Déployer avec Docker

```bash
docker compose -f docker-compose.simple.yml up -d
```

Les conteneurs exposent les ports sur `127.0.0.1` uniquement. Configurer Nginx pour proxifier :
- `dash.votredomaine.com` -> `localhost:3000` (frontend)
- `api.votredomaine.com` -> `localhost:8000` (backend)

### 4. Lancer l'agent hardware (PC local)

```bash
cd hw-agent
cp .env.example .env
# Editer .env avec WS_URL et HW_AGENT_TOKEN

python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python agent.py
```

L'agent se connecte en WebSocket et envoie les stats hardware toutes les 2 secondes.

## Mode Démo

Le frontend intègre un **mode démo** pour prévisualiser l'interface sans backend :

```bash
cd dashboard-v2/frontend
NEXT_PUBLIC_DEMO=true npm run dev
```

Une version démo est déployée automatiquement sur Vercel à chaque push : [**trackboard.vercel.app**](https://trackboard-burn-30-nathan-saccols-projects.vercel.app)

## Structure du projet

```
dashboard-v2/
├── backend/                # API FastAPI
│   ├── app/
│   │   ├── main.py         # Point d'entrée, CORS, startup
│   │   ├── config.py       # Configuration (Pydantic Settings)
│   │   ├── database.py     # Async SQLAlchemy
│   │   ├── models.py       # Modèles BDD
│   │   ├── auth/           # Auth JWT + rate limiting
│   │   ├── api/            # Routes REST (stats trackers)
│   │   ├── hardware/       # WebSocket monitoring hardware
│   │   └── scrapers/       # Scrapers Playwright + scheduler
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # Dashboard Next.js
│   ├── src/
│   │   ├── app/            # Pages (/, /traffic, /hardware-monitor)
│   │   ├── components/     # Composants UI
│   │   ├── hooks/          # Hooks custom (useHardwareStats, etc.)
│   │   └── lib/            # Client API, données démo, auth
│   └── Dockerfile
├── hw-agent/               # Agent monitoring hardware
│   ├── agent.py            # Collecte stats + envoi WebSocket
│   └── requirements.txt
├── docker-compose.simple.yml  # Production (Nginx proxy)
├── docker-compose.dev.yml     # Développement local
└── .env.example               # Template de configuration
```

## Sécurité

- Auth JWT sur toutes les routes API et WebSocket
- Rate limiting sur `/auth/login` (5 tentatives/min/IP)
- CORS configuré par domaine (pas de wildcard)
- Ports Docker exposés sur `127.0.0.1` uniquement
- Agent hardware authentifié par token
- Aucun secret dans le code source (tout via `.env`)

## Licence

MIT
