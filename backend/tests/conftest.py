"""
Fixtures partagees pour les tests.
- Base SQLite en memoire
- Client HTTP async (httpx)
- Token d'authentification
"""
import os
import pytest
from datetime import datetime, timedelta
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Forcer les settings de test AVANT tout import applicatif
os.environ.update({
    "DATABASE_URL": "sqlite:///./test.db",
    "JWT_SECRET": "test-secret-key-for-unit-tests-minimum-32-characters",
    "ADMIN_PASSWORD": "testpass",
    "HW_AGENT_TOKEN": "test-hw-token",
    "SESSION_SYNC_TOKEN": "test-session-sync-token-0123456789abcdef",
    "SESSION_DEPOT_CLE": "test-cle-de-depot-0123456789abcdef-xyz",
    "SESSION_ALERTE_HEURES": "24",
    "SCRAPE_INTERVAL": "0",  # Desactiver le scheduler en test
    "DOMAIN": "test.local",
})

from app.db.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.db.models import TrackerStats  # noqa: E402
from app.auth.routes import _login_attempts  # noqa: E402

# Engine SQLite en memoire pour les tests
test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    """Override de la dependency DB pour utiliser la base de test."""
    async with TestSession() as session:
        try:
            yield session
        finally:
            await session.close()


# Remplacer la dependency DB dans l'app
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    """Cree et nettoie la base de test avant/apres chaque test."""
    _login_attempts.clear()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Client HTTP async pour tester l'API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_token(client: AsyncClient) -> str:
    """Retourne un token JWT valide."""
    resp = await client.post("/auth/login", json={"password": "testpass"})
    return resp.json()["token"]["access_token"]


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """Headers avec le token Bearer."""
    return {"Authorization": f"Bearer {auth_token}"}


# Dates relatives : l'historique ne remonte que 30 jours, des dates fixes
# sortaient de la fenetre avec le temps.
_RECENT = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(days=1)


@pytest.fixture
async def seeded_db():
    """Insere des donnees de test dans la base."""
    async with TestSession() as session:
        stats = [
            # Ancien snapshot d'abord (ID plus bas = plus ancien)
            TrackerStats(
                tracker_name="GF-FREE",
                ratio=2.3,
                buffer="140 Go",
                vol_upload="480 Go",
                vol_download="195 Go",
                points_bonus="1400",
                count_seed="40",
                scraped_at=_RECENT - timedelta(days=5),
            ),
            # Snapshots recents
            TrackerStats(
                tracker_name="GF-FREE",
                ratio=2.5,
                buffer="150 Go",
                vol_upload="500 Go",
                vol_download="200 Go",
                points_bonus="1500",
                count_seed="42",
                count_downloaded="30",
                seed_time_total="1 an 2 mois",
                seed_time_avg="5 j 3 h",
                scraped_at=_RECENT,
            ),
            TrackerStats(
                tracker_name="TOS",
                ratio=5.2,
                buffer="400 Go",
                vol_upload="520 Go",
                vol_download="100 Go",
                points_bonus="3000",
                count_seed="60",
                count_downloaded="15",
                seed_time_total="2 ans",
                seed_time_avg="10 j",
                scraped_at=_RECENT,
            ),
        ]
        session.add_all(stats)
        await session.commit()
