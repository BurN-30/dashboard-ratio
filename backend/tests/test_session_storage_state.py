"""Dépôt de session par storage_state complet (Playwright) face à la valeur simple, et relecture par C411."""
import json
import logging
import time
from datetime import datetime, timezone

import pytest

from app.scrapers import base, routes
from app.scrapers.base import ScrapedStats, ScraperConfig
from app.scrapers.c411 import C411Scraper
from app.scrapers.routes import ScrapeResult, nettoyer_storage_state

SESSION = "Fe26.2**session-inventee-pour-les-tests-0123456789abcdef"
SOUVENIR = "souvenir-invente-longue-duree-0123456789"
CLOUDFLARE = "defi-cloudflare-du-poste-windows-0123456789"
ETRANGER = "cookie-d-un-autre-site-0123456789"
SECRETS = (SESSION, SOUVENIR, CLOUDFLARE, ETRANGER)
MODELE = C411Scraper.SESSION_COOKIE
DANS_30_JOURS = int(time.time()) + 30 * 86400


def cookie(nom, valeur, domaine="c411.org", **champs):
    return {"name": nom, "value": valeur, "domain": domaine, "path": "/", "expires": DANS_30_JOURS,
            "httpOnly": True, "secure": True, "sameSite": "Lax", **champs}


def etat_complet(**session):
    """Ce que rend context.storage_state() sur le poste : session, cookie secondaire, bruit."""
    return {
        "cookies": [
            cookie("__Host-c411_session", SESSION, **{"expires": int(time.time()) + 7 * 86400, **session}),
            cookie("remember_web", SOUVENIR, domaine=".c411.org"),
            cookie("cf_clearance", CLOUDFLARE, domaine=".c411.org", sameSite="None"),
            cookie("sid", ETRANGER, domaine="exemple.org"),
            cookie("sid", ETRANGER, domaine="pasc411.org"),
        ],
        "origins": [
            {"origin": "https://c411.org", "localStorage": [{"name": "theme", "value": "sombre"}]},
            {"origin": "https://exemple.org", "localStorage": [{"name": "x", "value": ETRANGER}]},
        ],
    }


def scraper():
    return C411Scraper(ScraperConfig(name="C411", login_url="https://c411.org/login",
                                     profile_url_template="https://c411.org/api/auth/me", username="u", password="p"))


def par_nom(etat):
    return {c["name"]: c for c in etat["cookies"]}


@pytest.fixture
def dossier(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "COOKIES_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def route(dossier, monkeypatch):
    """Route de dépôt branchée sur un faux relevé de contrôle ; rend la liste des appels."""
    appels = []

    async def faux_releve(tracker_name=None):
        appels.append(tracker_name)
        routes._scrape_results[tracker_name].status = faux_releve.statut
        routes._scrape_results[tracker_name].last_error = (
            None if faux_releve.statut == "ok" else "session_expiree_reconnexion_manuelle")

    async def sans_base(nom):
        return None

    faux_releve.statut = "ok"
    monkeypatch.setattr(routes, "get_scraper", lambda nom: scraper())
    monkeypatch.setattr(routes, "run_scraping_task", faux_releve)
    monkeypatch.setattr(routes, "_persist_scraper_state", sans_base)
    monkeypatch.setitem(routes._scrape_results, "C411", ScrapeResult(
        tracker_name="C411", status="skipped", session_expiry_alert_at=datetime.now(timezone.utc)))
    return faux_releve, appels


class TestNettoyage:
    def test_cookies_du_site_gardes_le_reste_ecarte(self):
        etat = nettoyer_storage_state(etat_complet(), MODELE)
        cookies = par_nom(etat)
        assert set(cookies) == {"__Host-c411_session", "remember_web"}
        assert cookies["remember_web"]["value"] == SOUVENIR and cookies["remember_web"]["domain"] == ".c411.org"
        assert cookies["remember_web"]["expires"] == DANS_30_JOURS
        assert [o["origin"] for o in etat["origins"]] == ["https://c411.org"]
        assert ETRANGER not in json.dumps(etat) and CLOUDFLARE not in json.dumps(etat)

    def test_cookie_de_session_remis_au_gabarit(self):
        # Préfixe __Host- : hôte exact, chemin /, Secure, quoi qu'annonce l'état reçu.
        etat = nettoyer_storage_state(etat_complet(domain=".c411.org", path="/x", secure=False, httpOnly=False), MODELE)
        c = par_nom(etat)["__Host-c411_session"]
        assert (c["value"], c["domain"], c["path"], c["secure"], c["httpOnly"]) == (SESSION, "c411.org", "/", True, True)
        assert abs(c["expires"] - (time.time() + 7 * 86400)) < 60  # échéance réelle du navigateur gardée

    def test_cookie_de_session_sans_echeance(self):
        c = par_nom(nettoyer_storage_state(etat_complet(expires=-1), MODELE))["__Host-c411_session"]
        assert abs(c["expires"] - (time.time() + 7 * 86400)) < 60

    def test_cookie_secondaire_mal_forme_ecarte_sans_refus(self):
        etat = etat_complet()
        etat["cookies"] += [cookie("mauvais", "a;b"), cookie("retour", "a\r\nSet-Cookie: x=y"), cookie("", "vide"),
                            cookie("perime", "valeur", expires=1), "pas un cookie", cookie("liste", ["x"])]
        assert set(par_nom(nettoyer_storage_state(etat, MODELE))) == {"__Host-c411_session", "remember_web"}

    @pytest.mark.parametrize("etat", [
        None, "texte", [], {}, {"cookies": "non"}, {"cookies": []},
        {"cookies": [cookie("remember_web", SOUVENIR)]},                                   # pas de session
        {"cookies": [cookie("__Host-c411_session", SESSION, domaine="exemple.org")]},      # session d'un autre site
        {"cookies": [cookie("__Host-c411_session", f"{SESSION}; Path=/")]},                # valeur interdite
        {"cookies": [cookie("__Host-c411_session", "court")]},
        {"cookies": [cookie("__Host-c411_session", SESSION, expires=1)]},                  # déjà expirée
        {"cookies": [cookie("__Host-c411_session", SESSION), cookie("__Host-c411_session", SESSION + "2")]},
        {"cookies": [cookie("__Host-c411_session", SESSION)] * 501},
    ])
    def test_etats_refuses(self, etat):
        assert nettoyer_storage_state(etat, MODELE) is None


class TestRouteDeDepot:
    @pytest.mark.parametrize("statut, attendu", [("ok", "ok"), ("skipped", "refusee")])
    async def test_storage_state_complet(self, client, auth_headers, dossier, route, caplog, statut, attendu):
        releve, appels = route
        releve.statut = statut
        with caplog.at_level(logging.DEBUG):
            resp = await client.post("/scrapers/session/C411", json={"storage_state": etat_complet()},
                                     headers=auth_headers)

        assert resp.status_code == 200 and resp.json()["status"] == attendu
        assert appels == ["C411"]
        ecrit = json.loads((dossier / "c411.json").read_text())
        cookies = par_nom(ecrit)
        # Le cookie secondaire de longue durée est gardé à côté du cookie de session.
        assert cookies["__Host-c411_session"]["value"] == SESSION
        assert cookies["remember_web"]["value"] == SOUVENIR
        assert set(cookies) == {"__Host-c411_session", "remember_web"}
        assert ecrit["origins"] == [{"origin": "https://c411.org", "localStorage": [{"name": "theme", "value": "sombre"}]}]
        # Ni la réponse ni les journaux ne contiennent une valeur reçue.
        for secret in SECRETS:
            assert secret not in resp.text and secret not in caplog.text
        sr = routes._scrape_results["C411"]
        assert sr.session_expiry_alert_at is None
        assert (sr.session_deposited_at is not None) == (statut == "ok")

    async def test_valeur_simple_toujours_acceptee(self, client, auth_headers, dossier, route, caplog):
        _, appels = route
        with caplog.at_level(logging.DEBUG):
            resp = await client.post("/scrapers/session/C411", json={"valeur": SESSION}, headers=auth_headers)
        assert resp.status_code == 200 and resp.json()["status"] == "ok"
        assert appels == ["C411"]
        (c,) = json.loads((dossier / "c411.json").read_text())["cookies"]
        assert (c["name"], c["value"]) == ("__Host-c411_session", SESSION)
        assert SESSION not in resp.text and SESSION not in caplog.text

    async def test_les_deux_formats_donnent_la_meme_session(self, client, auth_headers, dossier, route):
        await client.post("/scrapers/session/C411", json={"valeur": SESSION}, headers=auth_headers)
        simple = par_nom(json.loads((dossier / "c411.json").read_text()))["__Host-c411_session"]
        (dossier / "c411.json").unlink()
        await client.post("/scrapers/session/C411", json={"storage_state": etat_complet()}, headers=auth_headers)
        complet = par_nom(json.loads((dossier / "c411.json").read_text()))["__Host-c411_session"]
        sans_date = lambda c: {k: v for k, v in c.items() if k != "expires"}
        assert sans_date(simple) == sans_date(complet)

    async def test_storage_state_refuse_jamais_recopie(self, client, auth_headers, dossier, route):
        _, appels = route
        sans_session = {"cookies": [cookie("remember_web", SOUVENIR)], "origins": []}
        mauvaise_valeur = etat_complet(value=f"{SESSION}; Path=/")
        for corps in ({"storage_state": sans_session}, {"storage_state": mauvaise_valeur},
                      {"storage_state": SESSION}, {"storage_state": None},
                      {"storage_state": etat_complet(), "valeur": SESSION}):
            resp = await client.post("/scrapers/session/C411", json=corps, headers=auth_headers)
            assert resp.status_code == 400
            for secret in SECRETS:
                assert secret not in resp.text
        assert appels == [] and not (dossier / "c411.json").exists()

    async def test_jeton_obligatoire(self, client, dossier):
        resp = await client.post("/scrapers/session/C411", json={"storage_state": etat_complet()})
        assert resp.status_code in (401, 403) and not (dossier / "c411.json").exists()

    async def test_releve_en_cours(self, client, auth_headers, dossier, route, monkeypatch):
        monkeypatch.setattr(routes, "_scraping_in_progress", True)
        resp = await client.post("/scrapers/session/C411", json={"storage_state": etat_complet()},
                                 headers=auth_headers)
        assert resp.status_code == 409 and not (dossier / "c411.json").exists()

    async def test_fusion_avec_le_fichier_existant(self, client, auth_headers, dossier, route):
        """Ancienne session remplacée, cookie obtenu par le collecteur gardé, cookie commun mis à jour."""
        (dossier / "c411.json").write_text(json.dumps({"cookies": [
            cookie("__Host-c411_session", "ancienne-session-0123456789abcdef"),
            cookie("cf_clearance", "defi-passe-par-le-vps", domaine=".c411.org"),
            cookie("remember_web", "ancien-souvenir", domaine=".c411.org"),
        ], "origins": [{"origin": "https://c411.org", "localStorage": [{"name": "theme", "value": "clair"}]}]}))
        resp = await client.post("/scrapers/session/C411", json={"storage_state": etat_complet()},
                                 headers=auth_headers)
        assert resp.status_code == 200
        ecrit = json.loads((dossier / "c411.json").read_text())
        assert {c["name"]: c["value"] for c in ecrit["cookies"]} == {
            "cf_clearance": "defi-passe-par-le-vps", "remember_web": SOUVENIR, "__Host-c411_session": SESSION}
        assert len(ecrit["cookies"]) == 3 and len(ecrit["origins"]) == 1
        assert ecrit["origins"][0]["localStorage"] == [{"name": "theme", "value": "sombre"}]
        assert not list(dossier.glob("*.tmp"))


class FauxContexte:
    def __init__(self, etat):
        self.etat, self.ferme = etat, False

    async def new_page(self):
        return object()

    async def storage_state(self):
        return self.etat

    async def close(self):
        self.ferme = True


class FauxNavigateur:
    def __init__(self):
        self.contextes = []

    async def new_context(self, storage_state=None):
        self.contextes.append(FauxContexte(storage_state))
        return self.contextes[-1]


class TestReleveC411:
    """C411Scraper.run() charge le storage_state déposé en entier et le réécrit sans rien perdre."""

    def depot(self):
        s = scraper()
        s.deposer_storage_state(nettoyer_storage_state(etat_complet(), MODELE))
        return s

    async def test_etat_complet_charge_puis_reecrit(self, dossier, monkeypatch):
        s, navigateur = self.depot(), FauxNavigateur()
        avant = json.loads((dossier / "c411.json").read_text())

        async def faux_scrape(page):
            return ScrapedStats(tracker_name="C411", ratio="2.00")

        monkeypatch.setattr(s, "scrape", faux_scrape)
        stats = await s.run(navigateur)

        (contexte,) = navigateur.contextes
        assert stats.ratio == "2.00" and contexte.ferme
        # Le contexte reçoit l'état entier (objet, pas un tri du seul cookie de session).
        assert contexte.etat == avant
        assert set(par_nom(contexte.etat)) == {"__Host-c411_session", "remember_web"}
        assert json.loads((dossier / "c411.json").read_text()) == avant

    async def test_session_expiree(self, dossier, monkeypatch):
        s, navigateur = self.depot(), FauxNavigateur()

        async def refus(page):
            raise PermissionError("session C411 expiree")

        monkeypatch.setattr(s, "scrape", refus)
        stats = await s.run(navigateur)
        assert stats.raw_data == {"error": "session_expiree_reconnexion_manuelle"}
        assert not (dossier / "c411.json").exists() and navigateur.contextes[0].ferme

    async def test_panne_reseau_ne_supprime_rien(self, dossier, monkeypatch):
        s, navigateur = self.depot(), FauxNavigateur()

        async def panne(page):
            raise RuntimeError("api_auth_me_http_502")

        monkeypatch.setattr(s, "scrape", panne)
        stats = await s.run(navigateur)
        assert stats.raw_data == {"error": "api_auth_me_http_502"}
        assert set(par_nom(json.loads((dossier / "c411.json").read_text()))) == {"__Host-c411_session", "remember_web"}

    @pytest.mark.parametrize("contenu", ["{pas du json", "[]", '{"cookies": "non"}'])
    async def test_fichier_illisible(self, dossier, contenu, caplog):
        (dossier / "c411.json").write_text(contenu)
        navigateur = FauxNavigateur()
        stats = await scraper().run(navigateur)
        assert stats.raw_data == {"error": "session_illisible_reconnexion_manuelle"}
        assert navigateur.contextes == [] and contenu not in caplog.text
