# Dashboard V2 - Torrent Stats & Hardware Monitor

Architecture unifiee pour le monitoring des trackers torrent et du hardware.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Serveur (Docker)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │   Traefik   │  │   FastAPI    │  │     PostgreSQL        │  │
│  │ (HTTPS/SSL) │  │  (Backend)   │  │     (Database)        │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
│                          │                                      │
│                   WebSocket ↑↓                                  │
└─────────────────────────────────────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │  PC Local   │
                    │  hw-agent   │
                    │  (Python)   │
                    └─────────────┘
```

## Quick Start

### 1. Configuration

```bash
# Copier et editer la configuration
cp .env.example .env
nano .env
```

### 2. Developpement Local

```bash
# Lancer avec Docker Compose (mode dev)
docker-compose -f docker-compose.dev.yml up -d

# L'API est disponible sur http://localhost:8000
# Documentation: http://localhost:8000/docs
```

### 3. Production Deployment

```bash
# 1. Copier et configurer l'environnement
cp .env.example .env
nano .env  # Remplir TOUTES les valeurs

# Variables critiques:
# - JWT_SECRET: au moins 32 caracteres aleatoires
# - DOMAIN: votre domaine (ex: dashboard.monsite.com)
# - ACME_EMAIL: email pour Let's Encrypt
# - ADMIN_PASSWORD: mot de passe du dashboard
# - Credentials des trackers (SW_*, GF_*, TOS_*, etc.)

# 2. Build et lancer les containers
docker-compose build
docker-compose up -d

# 3. Verifier les logs
docker-compose logs -f

# 4. (Optionnel) Avec l'agent hardware dans Docker
docker-compose --profile with-agent up -d
```

**URLs en production:**
- Frontend: `https://dashboard.yourdomain.com`
- API: `https://api.dashboard.yourdomain.com`
- Documentation API: `https://api.dashboard.yourdomain.com/docs`

### 4. Agent Hardware (PC Local)

```bash
cd hw-agent
cp .env.example .env
# Configurer WS_URL et HW_AGENT_TOKEN

# Windows
start_agent.bat

# Linux/Mac
pip install -r requirements.txt
python agent.py
```

## API Endpoints

### Authentication
- `POST /auth/login` - Login (retourne JWT)
- `POST /auth/logout` - Logout
- `GET /auth/me` - User info

### Trackers
- `GET /api/stats` - Dernieres stats de tous les trackers
- `GET /api/history` - Historique des stats
- `GET /api/stats/{tracker}` - Stats d'un tracker specifique
- `POST /scrapers/run` - Lancer le scraping

### Hardware
- `GET /hardware/stats` - Stats hardware (REST)
- `WS /hardware/ws/client` - Stats temps reel (WebSocket)
- `WS /hardware/ws/agent` - Connexion agent

## Structure du Projet

```
dashboard-v2/
├── docker-compose.yml      # Production
├── docker-compose.dev.yml  # Developpement
├── .env.example            # Configuration template
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py         # Point d'entree FastAPI
│       ├── config.py       # Configuration Pydantic
│       ├── auth/           # JWT Authentication
│       ├── scrapers/       # Scrapers modulaires
│       ├── hardware/       # WebSocket hardware
│       ├── api/            # Routes API principales
│       └── db/             # Models SQLAlchemy
├── frontend/               # (Next.js existant)
└── hw-agent/
    ├── agent.py            # Agent hardware Python
    └── requirements.txt
```

## Ajout d'un Nouveau Tracker

1. Editer `backend/app/scrapers/registry.py`
2. Ajouter la configuration du site:

```python
{
    "name": "NouveauTracker",
    "scraper_class": Unit3DScraper,  # ou nouveau scraper
    "login_url": "https://example.com/login",
    "profile_url_template": "https://example.com/users/{username}",
    "env_prefix": "NT",  # Pour NT_USER, NT_PASS, NT_USERNAME
},
```

3. Ajouter les credentials dans `.env`

## Migration depuis V1

1. Exporter les donnees existantes (stats.json, history.json)
2. Lancer le script de migration (TODO)
3. Configurer les credentials dans `.env`
4. Supprimer les anciens services (hwMonitor, hw_pusher, etc.)

## Securite

- JWT avec expiration configurable
- Token separe pour l'agent hardware
- HTTPS force via Traefik/Let's Encrypt
- CORS restreint aux domaines autorises

## Troubleshooting

### Le backend ne demarre pas
```bash
# Verifier les logs
docker-compose logs backend

# Causes frequentes:
# - JWT_SECRET trop court (min 32 chars)
# - DATABASE_URL incorrect
# - Port 8000 deja utilise
```

### Le scraping echoue
```bash
# Verifier les credentials dans .env
# Tester manuellement:
curl -X POST http://localhost:8000/scrapers/run \
  -H "Authorization: Bearer <token>"
```

### L'agent hardware ne se connecte pas
```bash
# Verifier le token
# Dans .env du serveur: HW_AGENT_TOKEN=xxx
# Dans hw-agent/.env: HW_AGENT_TOKEN=xxx (meme valeur)

# Verifier l'URL WebSocket
# BACKEND_WS_URL=wss://api.yourdomain.com/hardware/ws/agent
```

### Certificats SSL ne fonctionnent pas
```bash
# Verifier les logs Traefik
docker-compose logs traefik

# S'assurer que:
# - Le domaine pointe vers le serveur (DNS)
# - Les ports 80/443 sont ouverts
# - ACME_EMAIL est valide
```
