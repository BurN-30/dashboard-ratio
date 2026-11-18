"""
Configuration et gestion de la base de donnees avec SQLAlchemy async.
"""
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

# Convertir l'URL PostgreSQL sync en async
database_url = settings.database_url
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif database_url.startswith("sqlite://"):
    database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

# Engine async
engine = create_async_engine(
    database_url,
    echo=False,  # True pour debug SQL
    pool_pre_ping=True,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Classe de base pour tous les modeles SQLAlchemy."""
    pass


# Colonnes ajoutees apres la creation des tables. create_all ne modifie pas une table
# existante et Alembic n'est pas amorce (aucune revision, dossier absent de l'image) :
# les ajouts de colonnes facultatives passent par cette liste, rejouee sans effet a
# chaque demarrage. (table, colonne, type SQL)
COLONNES_AJOUTEES = [
    ("scraper_state", "last_failure_alert_at", "TIMESTAMP WITH TIME ZONE"),
    ("scraper_state", "last_warning_alert_at", "TIMESTAMP WITH TIME ZONE"),
    ("scraper_state", "session_deposited_at", "TIMESTAMP WITH TIME ZONE"),
    ("scraper_state", "session_expiry_alert_at", "TIMESTAMP WITH TIME ZONE"),
]


def ajouter_colonnes_manquantes(connexion) -> list[str]:
    """Ajoute les colonnes de COLONNES_AJOUTEES absentes (connexion synchrone). Retourne les ajouts."""
    inspecteur = inspect(connexion)
    ajouts = []
    for table, colonne, type_sql in COLONNES_AJOUTEES:
        if not inspecteur.has_table(table):
            continue
        if colonne in {c["name"] for c in inspecteur.get_columns(table)}:
            continue
        connexion.execute(text(f"ALTER TABLE {table} ADD COLUMN {colonne} {type_sql}"))
        ajouts.append(f"{table}.{colonne}")
    return ajouts


async def init_db():
    """Initialise la base de donnees (cree les tables, ajoute les colonnes manquantes)."""
    # Import des modeles pour les enregistrer
    from app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        ajouts = await conn.run_sync(ajouter_colonnes_manquantes)
    if ajouts:
        import logging
        logging.getLogger("dashboard").info("Schema : colonnes ajoutees : %s", ", ".join(ajouts))


async def get_db():
    """Dependency pour obtenir une session DB."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
