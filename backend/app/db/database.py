"""
Configuration et gestion de la base de donnees avec SQLAlchemy async.
"""
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


async def init_db():
    """Initialise la base de donnees (cree les tables)."""
    # Import des modeles pour les enregistrer
    from app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency pour obtenir une session DB."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
