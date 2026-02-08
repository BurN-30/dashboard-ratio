# Torrent Dashboard + Hardware Monitor

Dashboard personnel pour suivre vos stats de trackers torrent prives et monitorer votre hardware en temps reel.

## Fonctionnalites

**Tracker Stats**
- Ratio, buffer, upload/download, points bonus pour chaque tracker
- Graphiques d'evolution (ratio, buffer) sur 30 jours
- Support UNIT3D (Generation-Free, TheOldSchool, Gemini) + Sharewood + Torr9
- Liens rapides vers les shops bonus
- Scraping automatique a heures fixes (configurable)

**Hardware Monitor**
- CPU : charge, temperature, puissance, frequence, ventilateur, charge par coeur
- GPU : charge, temperature, VRAM, puissance, ventilateur
- RAM : utilisation en temps reel
- Stockage : espace disque, temperatures HDD/NVMe
- Reseau : upload/download en temps reel
- Uptime systeme

## Architecture

```
[PC local]                      [VPS]
hw-agent ──WebSocket──> Nginx ──> Backend (FastAPI)
                                     ├── PostgreSQL
                                     ├── Scrapers (Playwright)
                                     └── API REST + WebSocket
                                  Nginx ──> Frontend (Next.js)
```

- **Backend** : FastAPI, async SQLAlchemy, JWT auth, WebSocket
- **Frontend** : Next.js avec TailAdmin, ApexCharts, dark/light mode
- **Scrapers** : Playwright headless (Chromium), UNIT3D + Sharewood
- **HW Agent** : Script Python (psutil, nvidia-smi, LibreHardwareMonitor WMI)
- **Infra** : Docker Compose, Nginx reverse proxy, Let's Encrypt SSL

## Prerequis

- **Serveur/VPS** avec Docker et Docker Compose
- **Nginx** en reverse proxy (avec SSL via Let's Encrypt)
- **Python 3.10+** sur le PC local (pour le hw-agent)
- **LibreHardwareMonitor** en cours d'execution sur le PC (pour les temperatures CPU/disques)
- Comptes sur les trackers prives que vous souhaitez monitorer

## Installation

### 1. Cloner le projet

```bash
git clone https://github.com/your-username/dashboard-ratio.git
cd dashboard-ratio/dashboard-v2
```

### 2. Configurer

```bash
cp .env.example .env
# Editer .env avec vos identifiants et configuration
```

Variables importantes dans `.env` :

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | URL PostgreSQL |
| `JWT_SECRET` | Cle secrete JWT (min 32 chars, generez avec `openssl rand -hex 32`) |
| `ADMIN_PASSWORD` | Mot de passe admin du dashboard |
| `DOMAIN` | Votre domaine (ex: `dashboard.example.com`) |
| `HW_AGENT_TOKEN` | Token pour l'agent hardware (generez avec `openssl rand -hex 16`) |
| `TRACKER_USERNAME` | Votre username sur les trackers (pour les liens shop) |
| `SW_USER/PASS` | Identifiants Sharewood |
| `GF_USER/PASS` | Identifiants Generation-Free |
| `TOS_USER/PASS` | Identifiants TheOldSchool |
| `TORR9_USER/PASS` | Identifiants Torr9 |
| `GEMINI_USER/PASS` | Identifiants Gemini Tracker |

### 3. Deployer avec Docker

```bash
docker compose -f docker-compose.simple.yml up -d
```

Les containers exposent les ports sur `127.0.0.1` uniquement. Configurez Nginx pour proxy :
- `dash.votredomaine.com` -> `localhost:3000` (frontend)
- `api.votredomaine.com` -> `localhost:8000` (backend)

### 4. Lancer le Hardware Agent (PC local)

```bash
cd hw-agent
cp .env.example .env
# Editer .env avec WS_URL et HW_AGENT_TOKEN

python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python agent.py
```

L'agent se connecte en WebSocket au backend et envoie les stats hardware toutes les 2 secondes.

## Developpement local

```bash
# Backend seul
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend seul
cd frontend
npm install
npm run dev

# Ou tout via Docker (mode dev)
docker compose -f docker-compose.dev.yml up
```

## Structure du projet

```
dashboard-v2/
├── backend/                # API FastAPI
│   ├── app/
│   │   ├── main.py         # Point d'entree, CORS, startup
│   │   ├── config.py       # Configuration (Pydantic Settings)
│   │   ├── database.py     # SQLAlchemy async
│   │   ├── models.py       # Modeles DB
│   │   ├── auth/           # JWT auth + rate limiting
│   │   ├── api/            # Routes REST (trackers stats)
│   │   ├── hardware/       # WebSocket hardware monitoring
│   │   └── scrapers/       # Playwright scrapers + scheduler
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # Next.js dashboard
│   ├── src/
│   │   ├── app/            # Pages (/, /traffic, /hardware-monitor)
│   │   ├── components/     # UI components
│   │   ├── hooks/          # Custom hooks (useHardwareStats, etc.)
│   │   └── lib/            # API client, auth utils
│   └── Dockerfile
├── hw-agent/               # Hardware monitoring agent
│   ├── agent.py            # Collecte stats + envoi WebSocket
│   └── requirements.txt
├── docker-compose.simple.yml  # Production (Nginx proxy)
├── docker-compose.dev.yml     # Developpement local
└── .env.example               # Template de configuration
```

## Securite

- JWT auth sur toutes les routes API et WebSocket
- Rate limiting sur `/auth/login` (5 tentatives/min/IP)
- CORS configure par domaine (pas de wildcard)
- Ports Docker exposes en `127.0.0.1` uniquement
- Agent hardware authentifie par token
- Pas de secrets dans le code source (tout via `.env`)

## Licence

MIT
