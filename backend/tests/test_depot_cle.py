"""SESSION_DEPOT_CLE : en-tête X-Depot-Cle accepté sur le dépôt de session, et nulle part ailleurs."""
import json
import logging
import re

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.main import app
from app.scrapers import base, routes
from app.scrapers.base import ScraperConfig
from app.scrapers.c411 import C411Scraper
from app.scrapers.routes import ScrapeResult

CLE = "test-cle-de-depot-0123456789abcdef-xyz"  # celle de conftest.py
ENTETES = {"X-Depot-Cle": CLE}
SESSION = "Fe26.2**session-inventee-pour-les-tests-0123456789abcdef"
ROUTE_DE_DEPOT = ("post", "/scrapers/session/{tracker_name}")
AUTRES_ROUTES = sorted(
    (methode, chemin)
    for chemin, operations in app.openapi()["paths"].items()
    for methode, op in operations.items()
    if op.get("security") and (methode, chemin) != ROUTE_DE_DEPOT
)


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


async def test_bonne_cle_sans_bearer(client, depot, caplog):
    with caplog.at_level(logging.DEBUG):
        resp = await client.post("/scrapers/session/C411", json={"valeur": SESSION}, headers=ENTETES)
    assert resp.status_code == 200 and resp.json()["status"] == "ok"
    (cookie,) = json.loads((depot / "c411.json").read_text())["cookies"]
    assert cookie["value"] == SESSION
    # Ni la clé ni le cookie dans la réponse ou les journaux.
    for secret in (CLE, SESSION):
        assert secret not in resp.text and secret not in caplog.text
    assert "depot-cle" in caplog.text  # le journal dit seulement par quel moyen


@pytest.mark.parametrize("cle", [CLE + "x", CLE[:-1], CLE.upper(), "", " ", "test-hw-token", "testpass",
                                 "test-session-sync-token-0123456789abcdef", "é" * 40])
async def test_mauvaise_cle_refusee(client, depot, caplog, cle):
    with caplog.at_level(logging.DEBUG):
        resp = await client.post("/scrapers/session/C411", json={"valeur": SESSION},
                                 headers={b"X-Depot-Cle": cle.encode()})
    assert resp.status_code == 401 and not (depot / "c411.json").exists()
    assert SESSION not in resp.text and SESSION not in caplog.text
    if cle.strip():
        assert cle not in resp.text and cle not in caplog.text


@pytest.mark.parametrize("configuree", [None, ""])
async def test_mode_desactive_quand_variable_vide(client, auth_headers, depot, monkeypatch, configuree):
    monkeypatch.setattr(get_settings(), "session_depot_cle", configuree)
    for cle in (CLE, ""):
        resp = await client.post("/scrapers/session/C411", json={"valeur": SESSION}, headers={"X-Depot-Cle": cle})
        assert resp.status_code == 401
    assert not (depot / "c411.json").exists()
    # Le jeton de l'interface, lui, marche toujours.
    resp = await client.post("/scrapers/session/C411", json={"valeur": SESSION}, headers=auth_headers)
    assert resp.status_code == 200 and resp.json()["status"] == "ok"


async def test_mauvaise_cle_n_empeche_pas_le_bearer(client, auth_headers, depot):
    resp = await client.post("/scrapers/session/C411", json={"valeur": SESSION},
                             headers={**auth_headers, "X-Depot-Cle": "mauvaise"})
    assert resp.status_code == 200 and resp.json()["status"] == "ok"


async def test_cle_refusee_comme_bearer(client, depot):
    """La clé ne vaut que dans son en-tête : présentée comme jeton Bearer, elle est refusée."""
    resp = await client.post("/scrapers/session/C411", json={"valeur": SESSION},
                             headers={"Authorization": f"Bearer {CLE}"})
    assert resp.status_code == 401 and not (depot / "c411.json").exists()


def test_inventaire():
    assert len(AUTRES_ROUTES) >= 15 and ("post", "/scrapers/run") in AUTRES_ROUTES


@pytest.mark.parametrize("methode, chemin", AUTRES_ROUTES)
async def test_cle_refusee_sur_les_autres_routes(client, depot, methode, chemin):
    url = re.sub(r"\{[^}]+\}", "C411", chemin)
    for entetes in (ENTETES, {"Authorization": f"Bearer {CLE}"}, {**ENTETES, "Authorization": f"Bearer {CLE}"}):
        resp = await client.request(methode.upper(), url, headers=entetes, json={})
        assert resp.status_code in (401, 403), f"{methode.upper()} {chemin} accepte SESSION_DEPOT_CLE"
    assert not (depot / "c411.json").exists()


def test_configuration(monkeypatch):
    for vide in ("", "   "):  # variable transmise vide par le compose : mode désactivé
        monkeypatch.setenv("SESSION_DEPOT_CLE", vide)
        assert Settings().session_depot_cle is None
    monkeypatch.setenv("SESSION_DEPOT_CLE", "trop-courte")
    with pytest.raises(ValidationError):
        Settings()
    monkeypatch.delenv("SESSION_DEPOT_CLE")
    assert Settings(_env_file=None).session_depot_cle is None
