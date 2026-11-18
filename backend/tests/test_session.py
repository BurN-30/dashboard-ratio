"""Session manuelle (C411, Ygg) : dépôt du cookie, route protégée, migration de scraper_state."""
import json
import logging
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine, inspect, text

from app.db.database import COLONNES_AJOUTEES, ajouter_colonnes_manquantes
from app.scrapers import base, routes
from app.scrapers.base import ScraperConfig
from app.scrapers.c411 import C411Scraper
from app.scrapers.routes import ScrapeResult, nettoyer_valeur_cookie
from app.scrapers.ygg import YggScraper

VALEUR = "Fe26.2**valeur-inventee-pour-les-tests-0123456789abcdef"


def scraper(classe=C411Scraper, nom="C411"):
    return classe(ScraperConfig(name=nom, login_url="https://c411.org/login",
                                profile_url_template="https://c411.org/api/auth/me", username="u", password="p"))


@pytest.fixture
def dossier(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "COOKIES_DIR", tmp_path)
    return tmp_path


def test_nettoyage_de_la_valeur_collee():
    assert nettoyer_valeur_cookie(f"  {VALEUR}\n", "__Host-c411_session") == VALEUR
    assert nettoyer_valeur_cookie(f'__Host-c411_session="{VALEUR}"', "__Host-c411_session") == VALEUR
    for refuse in (None, 12, "", "court", "deux mots separes par des espaces", f"{VALEUR}; Path=/",
                   f"{VALEUR}\r\nSet-Cookie: x=y", "é" * 40, "a" * 5000):
        assert nettoyer_valeur_cookie(refuse, "__Host-c411_session") is None


def test_fichier_au_format_storage_state(dossier):
    s = scraper()
    s.deposer_session(VALEUR)
    etat = json.loads((dossier / "c411.json").read_text())
    assert etat["origins"] == []
    (c,) = etat["cookies"]
    assert c["name"] == "__Host-c411_session" and c["value"] == VALEUR
    # Préfixe __Host- : cookie lié à l'hôte, chemin /, Secure.
    assert (c["domain"], c["path"], c["secure"], c["httpOnly"], c["sameSite"]) == ("c411.org", "/", True, True, "Lax")
    assert set(c) == {"name", "value", "domain", "path", "expires", "httpOnly", "secure", "sameSite"}
    assert not list(dossier.glob("*.tmp"))


def test_les_autres_cookies_sont_gardes(dossier):
    (dossier / "ygg.json").write_text(json.dumps({"cookies": [
        {"name": "__ygg_sess", "value": "ancienne", "domain": "www.yggreborn.org", "path": "/", "expires": 1,
         "httpOnly": True, "secure": True, "sameSite": "Lax"},
        {"name": "cf_clearance", "value": "garde", "domain": ".yggreborn.org", "path": "/", "expires": 2,
         "httpOnly": True, "secure": True, "sameSite": "None"},
    ], "origins": [{"origin": "https://www.yggreborn.org", "localStorage": []}]}))
    scraper(YggScraper, "YGG").deposer_session(VALEUR)
    etat = json.loads((dossier / "ygg.json").read_text())
    assert {c["name"]: c["value"] for c in etat["cookies"]} == {"cf_clearance": "garde", "__ygg_sess": VALEUR}
    assert len(etat["origins"]) == 1


def test_expiration_prevue(dossier):
    s = scraper()
    assert s.expiration_session() is None  # pas de fichier
    s.deposer_session(VALEUR)
    dans_7_jours = datetime.now(timezone.utc) + timedelta(days=7)
    assert abs((s.expiration_session() - dans_7_jours).total_seconds()) < 60
    # Durée fixe (C411) : la date de dépôt l'emporte si le fichier annonce plus tard.
    depot = datetime.now(timezone.utc) - timedelta(days=6)
    assert abs((s.expiration_session(depot) - (depot + timedelta(days=7))).total_seconds()) < 1
    # Durée glissante (Ygg) : seul le cookie compte.
    y = scraper(YggScraper, "YGG")
    y.deposer_session(VALEUR)
    assert abs((y.expiration_session(depot) - dans_7_jours).total_seconds()) < 60


class TestRouteDeDepot:
    async def test_jeton_obligatoire(self, client: AsyncClient):
        resp = await client.post("/scrapers/session/C411", json={"valeur": VALEUR})
        assert resp.status_code in (401, 403)

    async def test_tracker_sans_session_manuelle(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post("/scrapers/session/TOS", json={"valeur": VALEUR}, headers=auth_headers)
        assert resp.status_code == 404

    async def test_valeur_refusee_jamais_recopiee(self, client, auth_headers, dossier, monkeypatch):
        monkeypatch.setattr(routes, "get_scraper", lambda nom: scraper())
        mauvaise = f"{VALEUR}; Path=/"
        for corps in ({"valeur": mauvaise}, {"valeur": {"x": mauvaise}}, [mauvaise], {}):
            resp = await client.post("/scrapers/session/C411", json=corps, headers=auth_headers)
            assert resp.status_code == 400
            assert VALEUR not in resp.text
        resp = await client.post("/scrapers/session/C411", content=b"{pas du json " + VALEUR.encode(),
                                 headers=auth_headers)
        assert resp.status_code == 400 and VALEUR not in resp.text
        assert not (dossier / "c411.json").exists()

    @pytest.mark.parametrize("statut, attendu", [("ok", "ok"), ("skipped", "refusee")])
    async def test_depot_puis_releve_de_controle(self, client, auth_headers, dossier, monkeypatch, caplog,
                                                 statut, attendu):
        appels = []

        async def faux_releve(tracker_name=None):
            appels.append(tracker_name)
            routes._scrape_results[tracker_name].status = statut
            routes._scrape_results[tracker_name].last_error = None if statut == "ok" else "session_expiree_reconnexion_manuelle"

        async def sans_base(nom):
            return None

        monkeypatch.setattr(routes, "get_scraper", lambda nom: scraper())
        monkeypatch.setattr(routes, "run_scraping_task", faux_releve)
        monkeypatch.setattr(routes, "_persist_scraper_state", sans_base)
        monkeypatch.setitem(routes._scrape_results, "C411", ScrapeResult(
            tracker_name="C411", status="skipped", session_expiry_alert_at=datetime.now(timezone.utc)))

        with caplog.at_level(logging.DEBUG):
            resp = await client.post("/scrapers/session/C411", json={"valeur": VALEUR}, headers=auth_headers)

        assert resp.status_code == 200 and resp.json()["status"] == attendu
        assert appels == ["C411"]
        assert json.loads((dossier / "c411.json").read_text())["cookies"][0]["value"] == VALEUR
        # Ni la réponse ni les journaux ne contiennent la valeur.
        assert VALEUR not in resp.text and VALEUR not in caplog.text
        sr = routes._scrape_results["C411"]
        assert sr.session_expiry_alert_at is None
        assert (sr.session_deposited_at is not None) == (statut == "ok")

    async def test_releve_en_cours(self, client, auth_headers, dossier, monkeypatch):
        monkeypatch.setattr(routes, "get_scraper", lambda nom: scraper())
        monkeypatch.setattr(routes, "_scraping_in_progress", True)
        resp = await client.post("/scrapers/session/C411", json={"valeur": VALEUR}, headers=auth_headers)
        assert resp.status_code == 409 and not (dossier / "c411.json").exists()


def test_migration_de_scraper_state():
    """Table d'avant (sans les colonnes d'alerte) : colonnes ajoutées, lignes gardées, rejouable."""
    moteur = create_engine("sqlite://")
    with moteur.begin() as c:
        c.execute(text("CREATE TABLE scraper_state (tracker_name VARCHAR(100) PRIMARY KEY, "
                       "consecutive_failures INTEGER NOT NULL, last_success_at DATETIME, "
                       "last_known_active_warnings INTEGER NOT NULL, updated_at DATETIME NOT NULL)"))
        c.execute(text("INSERT INTO scraper_state VALUES ('C411', 26, NULL, 0, '2026-11-18')"))
        ajouts = ajouter_colonnes_manquantes(c)
        assert ajouts == [f"{t}.{col}" for t, col, _ in COLONNES_AJOUTEES]
    with moteur.begin() as c:
        assert ajouter_colonnes_manquantes(c) == []
        colonnes = {col["name"] for col in inspect(c).get_columns("scraper_state")}
        assert {"last_failure_alert_at", "last_warning_alert_at", "session_deposited_at",
                "session_expiry_alert_at"} <= colonnes
        assert c.execute(text("SELECT consecutive_failures, last_failure_alert_at FROM scraper_state")).one() == (26, None)


def test_modele_et_migration_alignes():
    from app.db.models import ScraperState

    for table, colonne, _ in COLONNES_AJOUTEES:
        assert table == ScraperState.__tablename__ and colonne in ScraperState.__table__.columns
