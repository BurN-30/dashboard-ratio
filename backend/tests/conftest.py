"""
Fixtures partagees pour les tests.
- Base SQLite en memoire
- Client HTTP async (httpx)
- Token d'authentification
"""
import os
import pytest
from datetime import datetime
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Forcer les settings de test AVANT tout import applicatif
os.environ.update({
    "DATABASE_URL": "sqlite:///./test.db",
    "JWT_SECRET": "test-secret-key-for-unit-tests-minimum-32-characters",
    "ADMIN_PASSWORD": "testpass",
    "HW_AGENT_TOKEN": "test-hw-token",
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
                scraped_at=datetime(2026, 2, 1, 10, 0, 0),
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
                scraped_at=datetime(2026, 2, 6, 10, 0, 0),
            ),
            TrackerStats(
                tracker_name="Sharewood",
                ratio=1.8,
                buffer="80 Go",
                vol_upload="300 Go",
                vol_download="166 Go",
                points_bonus="800",
                count_seed="25",
                count_downloaded="20",
                seed_time_total="8 mois",
                seed_time_avg="3 j 12 h",
                scraped_at=datetime(2026, 2, 6, 10, 0, 0),
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
                scraped_at=datetime(2026, 2, 6, 10, 0, 0),
            ),
        ]
        session.add_all(stats)
        await session.commit()
