"""
Dashboard V2 - FastAPI Backend
Point d'entree principal de l'API.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging_config import setup_logging

# Initialiser le logging avant les imports applicatifs
setup_logging()

from app.config import get_settings  # noqa: E402
from app.db.database import init_db  # noqa: E402
from app.auth.routes import router as auth_router  # noqa: E402
from app.scrapers.routes import router as scraper_router  # noqa: E402
from app.scrapers.scheduler import start_scheduler, stop_scheduler  # noqa: E402
from app.hardware.routes import router as hardware_router  # noqa: E402
from app.api.routes import router as api_router  # noqa: E402
from app.media.routes import router as media_router  # noqa: E402
from app.health import router as health_router, VERSION  # noqa: E402

logger = logging.getLogger("dashboard")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager - initialisation et cleanup."""
    # Startup
    logger.info("Initialisation de la base de donnees...")
    await init_db()
    logger.info("Base de donnees prete.")

    # Demarrer le planificateur de scraping automatique
    start_scheduler()
    logger.info("Planificateur de scraping demarre.")

    yield

    # Shutdown
    stop_scheduler()
    logger.info("Fermeture des connexions...")


# Creation de l'application FastAPI
app = FastAPI(
    title="TrackBoard API",
    description="API unifiee pour le monitoring trackers torrent + hardware + media",
    version=VERSION,
    lifespan=lifespan,
)

# Configuration CORS
settings = get_settings()

cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]
# Ajout des domaines de production
if settings.domain:
    cors_origins.extend([
        f"https://{settings.domain}",
        f"https://dash.{settings.domain}",
        f"https://api.{settings.domain}",
    ])
# Origines supplementaires via variable d'env
if settings.cors_origins:
    cors_origins.extend(settings.cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrement des routers
app.include_router(health_router, tags=["Health"])
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(scraper_router, prefix="/scrapers", tags=["Scrapers"])
app.include_router(hardware_router, prefix="/hardware", tags=["Hardware"])
app.include_router(api_router, prefix="/api", tags=["API"])
app.include_router(media_router, prefix="/media", tags=["Media"])


@app.get("/")
async def root():
    """Route racine - identification du service."""
    return {
        "service": "TrackBoard API",
        "version": VERSION,
        "docs": "/docs",
        "health": "/health",
    }
