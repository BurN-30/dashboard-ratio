"""SESSION_SYNC_TOKEN : jeton dédié au dépôt de session, refusé sur toute autre route protégée."""
import json
import re

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.main import app
from app.scrapers import base, routes
from app.scrapers.base import ScraperConfig
from app.scrapers.c411 import C411Scraper
from app.scrapers.routes import ScrapeResult

JETON = "test-session-sync-token-0123456789abcdef"  # celui de conftest.py
ENTETES = {"Authorization": f"Bearer {JETON}"}
SESSION = "Fe26.2**session-inventee-pour-les-tests-0123456789abcdef"
ROUTE_DE_DEPOT = ("post", "/scrapers/session/{tracker_name}")


def routes_protegees():
    """Toutes les opérations qui exigent un jeton Bearer, lues dans le schéma OpenAPI."""
    return sorted(
        (methode, chemin)
        for chemin, operations in app.openapi()["paths"].items()
        for methode, op in operations.items()
        if op.get("security")
    )


AUTRES_ROUTES = [r for r in routes_protegees() if r != ROUTE_DE_DEPOT]


@pytest.fixture
def depot(tmp_path, monkeypatch):
    """Route de dépôt branchée sur un faux relevé de contrôle réussi."""
    async def faux_releve(tracker_name=None):
        routes._scrape_results[tracker_name].status = "ok"

    async def sans_base(nom):
        return None

    monkeypatch.setattr(base, "COOKIES_DIR", tmp_path)
    monkeypatch.setattr(routes, "get_scraper", lambda nom: C411Scraper(ScraperConfig(
        name="C411", login_url="https://c411.org/login", profile_url_template="https://c411.org/api/auth/me")))
    monkeypatch.setattr(routes, "run_scraping_task", faux_releve)
    monkeypatch.setattr(routes, "_persist_scraper_state", sans_base)
    monkeypatch.setitem(routes._scrape_results, "C411", ScrapeResult(tracker_name="C411", status="skipped"))
    return tmp_path


def test_inventaire():
    """La route de dépôt est protégée, et il reste d'autres routes à qui refuser le jeton."""
    assert ROUTE_DE_DEPOT in routes_protegees()
    assert len(AUTRES_ROUTES) >= 15
    assert ("get", "/auth/me") in AUTRES_ROUTES and ("post", "/auth/refresh") in AUTRES_ROUTES
    assert ("post", "/scrapers/run") in AUTRES_ROUTES and ("get", "/api/stats") in AUTRES_ROUTES


@pytest.mark.parametrize("corps", [{"valeur": SESSION}, {"storage_state": {"cookies": [
    {"name": "__Host-c411_session", "value": SESSION, "domain": "c411.org", "path": "/", "expires": -1}]}}])
async def test_accepte_sur_le_depot_de_session(client, depot, caplog, corps):
    resp = await client.post("/scrapers/session/C411", json=corps, headers=ENTETES)
    assert resp.status_code == 200 and resp.json()["status"] == "ok"
    (cookie,) = json.loads((depot / "c411.json").read_text())["cookies"]
    assert cookie["value"] == SESSION
    assert JETON not in resp.text and JETON not in caplog.text


@pytest.mark.parametrize("methode, chemin", AUTRES_ROUTES)
async def test_refuse_sur_les_autres_routes_protegees(client, depot, methode, chemin):
    url = re.sub(r"\{[^}]+\}", "C411", chemin)
    resp = await client.request(methode.upper(), url, headers=ENTETES, json={})
    assert resp.status_code in (401, 403), f"{methode.upper()} {chemin} accepte SESSION_SYNC_TOKEN"
    assert not (depot / "c411.json").exists()


async def test_ne_donne_pas_de_jeton_d_interface(client):
    """Pas d'échange possible contre un JWT : /auth/refresh le refuse."""
    resp = await client.post("/auth/refresh", headers=ENTETES)
    assert resp.status_code == 401 and "access_token" not in resp.text


async def test_jeton_d_interface_toujours_accepte(client, auth_headers, depot):
    resp = await client.post("/scrapers/session/C411", json={"valeur": SESSION}, headers=auth_headers)
    assert resp.status_code == 200 and resp.json()["status"] == "ok"


@pytest.mark.parametrize("jeton", [JETON + "x", JETON[:-1], JETON.upper(), "test-hw-token", "testpass", "é" * 40])
async def test_mauvais_jeton_refuse(client, depot, jeton):
    resp = await client.post("/scrapers/session/C411", json={"valeur": SESSION},
                             headers={"Authorization": b"Bearer " + jeton.encode()})
    assert resp.status_code in (401, 403) and not (depot / "c411.json").exists()


@pytest.mark.parametrize("configure", [None, ""])
async def test_jeton_desactive_quand_non_configure(client, depot, monkeypatch, configure):
    monkeypatch.setattr(get_settings(), "session_sync_token", configure)
    for jeton in (JETON, ""):
        resp = await client.post("/scrapers/session/C411", json={"valeur": SESSION},
                                 headers={"Authorization": f"Bearer {jeton}"})
        assert resp.status_code in (401, 403)
    assert not (depot / "c411.json").exists()


def test_configuration(monkeypatch):
    for vide in ("", "   "):  # variable transmise vide par le compose : jeton désactivé
        monkeypatch.setenv("SESSION_SYNC_TOKEN", vide)
        assert Settings().session_sync_token is None
    monkeypatch.setenv("SESSION_SYNC_TOKEN", "trop-court")
    with pytest.raises(ValidationError):
        Settings()
    monkeypatch.delenv("SESSION_SYNC_TOKEN")
    assert Settings(_env_file=None).session_sync_token is None
