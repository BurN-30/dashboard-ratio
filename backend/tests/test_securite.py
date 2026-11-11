"""Surface publique de l'API : seules la sante, la racine et la connexion
repondent sans jeton ; la documentation interactive est coupee par defaut."""
import pytest
from httpx import AsyncClient

ROUTES_PROTEGEES = [
    "/scrapers/sites",
    "/scrapers/status",
    "/scrapers/available",
    "/hardware/status",
    "/hardware/stats",
    "/hardware/history",
    "/hardware/history/summary",
    "/api/stats",
    "/api/history",
    "/api/summary",
    "/media/overview",
    "/health/full",
    "/auth/me",
]


@pytest.mark.parametrize("route", ROUTES_PROTEGEES)
async def test_route_refusee_sans_jeton(client: AsyncClient, route: str):
    resp = await client.get(route)
    assert resp.status_code in (401, 403), f"{route} repond sans authentification"


@pytest.mark.parametrize("route", ["/docs", "/redoc", "/openapi.json"])
async def test_documentation_coupee(client: AsyncClient, route: str):
    resp = await client.get(route)
    assert resp.status_code == 404


async def test_inventaire_des_routes_publiques():
    """Toute nouvelle route sans authentification fait echouer ce test.

    Le schema OpenAPI (genere en memoire, meme quand /openapi.json est coupe)
    porte un champ `security` sur chaque operation protegee par le jeton Bearer.
    """
    from app.main import app

    publiques = sorted(
        f"{methode.upper()} {chemin}"
        for chemin, operations in app.openapi()["paths"].items()
        for methode, op in operations.items()
        if not op.get("security")
    )
    assert publiques == ["GET /", "GET /health", "POST /auth/login", "POST /auth/logout"]


async def test_route_accessible_avec_jeton(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/scrapers/status", headers=auth_headers)
    assert resp.status_code == 200


def test_agent_materiel_jeton():
    """L'agent materiel s'authentifie par HW_AGENT_TOKEN ; un mauvais jeton est refuse."""
    from starlette.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect
    from app.main import app

    tc = TestClient(app)  # sans `with` : pas de lifespan (ni base ni planificateur)
    for mauvais in ("mauvais-jeton", "test-hw-tokenX", "é"):
        with pytest.raises(WebSocketDisconnect) as exc:
            with tc.websocket_connect(f"/hardware/ws/agent?token={mauvais}") as ws:
                ws.receive_text()
        assert exc.value.code == 4001
    with tc.websocket_connect("/hardware/ws/agent?token=test-hw-token") as ws:
        ws.close()
