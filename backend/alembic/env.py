"""
Alembic environment - configure pour async SQLAlchemy + asyncpg.

L'URL de DB est lue depuis app.config.get_settings() (qui lit .env),
elle ne doit PAS etre stockee dans alembic.ini.
"""
import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Permet d'importer les modules app/ depuis backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des modeles pour qu'Alembic les voie via Base.metadata
from app.db.database import Base  # noqa: E402
from app.db import models  # noqa: E402,F401  (register all tables)
from app.config import get_settings  # noqa: E402

# Configuration Alembic
config = context.config

# Configurer le logging si alembic.ini en parle
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Resoudre l'URL de DB depuis l'app, override la valeur d'alembic.ini
settings = get_settings()
db_url = settings.database_url
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif db_url.startswith("sqlite://"):
    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
config.set_main_option("sqlalchemy.url", db_url)

# Metadata cible (toutes les tables declarees dans app.db.models)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Mode offline : genere du SQL sans se connecter a la DB."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute les migrations sur une connexion sync (run_sync wrap)."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Mode online async : ouvre une connexion via async_engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Lance les migrations en mode online."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
