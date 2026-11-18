"""Alertes Discord : anti-répétition (échecs, avertissements, session) et texte des messages."""
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.notifications import (
    decider_alerte_avertissements, decider_alerte_echec, embed_avertissements, embed_echec,
    embed_session_bientot_expiree, session_bientot_expiree, texte_rachat,
)
from app.scrapers.base import BaseScraper, ScraperConfig
from app.scrapers.c411 import C411Scraper
from app.scrapers.ygg import YggScraper

T0 = datetime(2026, 11, 18, 13, 0, 30, tzinfo=timezone.utc)
H = timedelta(hours=1)
LIEN_C411 = {"lien_reconnexion": "https://c411.org/login#trackboard"}


# --- échecs : une alerte au 3e, puis un rappel par 24 h

def test_echec_rien_avant_le_troisieme():
    assert decider_alerte_echec(1, None, T0) is None
    assert decider_alerte_echec(2, None, T0) is None


def test_echec_premiere_alerte_au_troisieme():
    assert decider_alerte_echec(3, None, T0) == "premiere"


def test_echec_une_seule_panne_trois_releves_par_jour():
    """Relevés à 8 h, 14 h et 20 h pendant 8 jours : 1 alerte puis 1 rappel par jour, pas 24."""
    derniere, envois, maintenant = None, [], T0
    for n in range(1, 27):
        decision = decider_alerte_echec(n, derniere, maintenant)
        if decision:
            envois.append((n, decision))
            derniere = maintenant
        # 14 h -> 20 h -> 8 h -> 14 h, à quelques secondes près
        maintenant += [6 * H, 12 * H, 6 * H][(n - 1) % 3] - timedelta(seconds=5)
    assert envois[0] == (3, "premiere")
    assert all(d == "rappel" for _, d in envois[1:])
    assert [n for n, _ in envois] == [3, 6, 9, 12, 15, 18, 21, 24]


def test_echec_rappel_pas_avant_24_h():
    assert decider_alerte_echec(4, T0, T0 + 6 * H) is None
    assert decider_alerte_echec(5, T0, T0 + 18 * H) is None
    assert decider_alerte_echec(6, T0, T0 + 24 * H) == "rappel"


def test_echec_etat_herite_sans_date_d_alerte():
    """Après la migration : 26 échecs et aucune date connue -> un rappel, puis le rythme normal."""
    assert decider_alerte_echec(27, None, T0) == "rappel"
    assert decider_alerte_echec(28, T0, T0 + 6 * H) is None


def test_echec_date_sans_fuseau():
    assert decider_alerte_echec(5, T0.replace(tzinfo=None), T0 + 2 * H) is None


def test_message_session_expiree():
    e = embed_echec("C411", 26, "session_absente_reconnexion_manuelle", rappel=True, reconnexion={
        "login_url": "https://c411.org/login", "cookie": "__Host-c411_session",
        "trackboard_url": "https://trackboard.example"})
    assert e["title"] == "Rappel : session expirée : C411"
    assert "reconnexion à faire" in e["description"]
    etapes = e["fields"][0]["value"]
    assert "https://c411.org/login" in etapes and "`__Host-c411_session`" in etapes
    assert "[TrackBoard](https://trackboard.example)" in etapes and "« Reconnecter »" in etapes
    assert "session_absente" not in str(e)
    assert "Se reconnecter" not in e["description"]  # pas de lien déclaré : message sans lien


def test_message_session_expiree_avec_lien():
    e = embed_echec("C411", 3, "session_expiree_reconnexion_manuelle", reconnexion={
        "login_url": "https://c411.org/login", "cookie": "__Host-c411_session",
        "trackboard_url": None, **LIEN_C411})
    assert e["title"] == "Session expirée : C411"
    assert "[Se reconnecter à C411](https://c411.org/login#trackboard)" in e["description"]
    assert "« Reconnecter »" in e["fields"][0]["value"]  # la marche à suivre manuelle reste
    # Le lien n'apparaît pas dans une panne ordinaire.
    e = embed_echec("C411", 3, "api_auth_me_http_502", reconnexion={"cookie": "c", **LIEN_C411})
    assert "trackboard" not in str(e)


def test_message_echec_ordinaire():
    e = embed_echec("TOS", 3, "Timeout 90000ms exceeded", reconnexion=None)
    assert e["title"] == "Relevé en échec : TOS"
    assert "**3** échecs consécutifs" in e["description"]
    assert "Timeout" in e["fields"][0]["value"]
    # Un tracker à session manuelle en panne pour une autre raison garde le message ordinaire.
    e = embed_echec("C411", 3, "api_auth_me_http_502", reconnexion={"login_url": "x", "cookie": "y"})
    assert e["title"] == "Relevé en échec : C411"


# --- avertissements : @here quand le compteur monte, rappel sans @here par 24 h

def test_avertissements_compteur_qui_monte():
    assert decider_alerte_avertissements(1, 0, None, T0) == "nouveau"
    assert decider_alerte_avertissements(3, 0, None, T0) == "critique"
    assert decider_alerte_avertissements(3, 2, T0 - H, T0) == "critique"


def test_avertissements_pas_de_repetition_a_chaque_releve():
    assert decider_alerte_avertissements(3, 3, T0, T0 + 6 * H) is None
    assert decider_alerte_avertissements(3, 3, T0, T0 + 18 * H) is None
    assert decider_alerte_avertissements(3, 3, T0, T0 + 24 * H - timedelta(seconds=5)) == "rappel"


def test_avertissements_baisse_et_fin():
    assert decider_alerte_avertissements(2, 3, T0, T0 + 6 * H) is None  # baisse : pas de nouvelle alerte
    assert decider_alerte_avertissements(2, 3, T0, T0 + 24 * H) == "rappel"
    assert decider_alerte_avertissements(1, 1, None, T0) is None  # un seul qui dure : pas de rappel
    assert decider_alerte_avertissements(0, 3, T0, T0 + 48 * H) is None


def test_avertissements_trois_jours_trois_releves_par_jour():
    derniere, envois, maintenant = None, [], T0
    precedent = 0
    for i in range(9):
        decision = decider_alerte_avertissements(3, precedent, derniere, maintenant)
        if decision:
            envois.append(decision)
            derniere = maintenant
        precedent = 3
        maintenant += [6 * H, 12 * H, 6 * H][i % 3]
    assert envois == ["critique", "rappel", "rappel"]


DETAIL = {
    "profil_url": "https://tracker.example/users/moi",
    "solde": 44994,
    "boutique_lue": True,
    "boutique_url": "https://tracker.example/users/moi/transactions/create",
    "rachat_hnr": {"libelle": "Rachat d'un H&R", "cost": 100000},
    "avertissements": [
        {"torrent": "Film.Un.2020.MULTi.1080p.WEB.H265-GRP", "url": "https://tracker.example/torrents/11",
         "cree_le": "2026-11-17 18:19:37", "expire_le": "2026-11-24 18:19:37"},
        {"torrent": "Serie.Deux.S01.[COMPLETE].VFF.1080p-GRP", "url": "https://tracker.example/torrents/22",
         "cree_le": "2026-11-17 18:19:37", "expire_le": "2026-11-24 18:19:37"},
    ],
}


def test_message_avertissements_complet():
    e = embed_avertissements("G3MINI TR4CK3R", 3, "critique", DETAIL)
    assert e["title"] == "Avertissements critiques : G3MINI TR4CK3R"
    assert "**3** avertissements actifs" in e["description"]
    torrents, rachat, profil = (c["value"] for c in e["fields"])
    assert "[Film.Un.2020.MULTi.1080p.WEB.H265-GRP](https://tracker.example/torrents/11)" in torrents
    assert "averti le 17/11 à 18:19, expire le 24/11 à 18:19" in torrents
    assert "(COMPLETE)" in torrents  # les crochets casseraient le lien
    assert "et 1 autre(s), voir le profil" in torrents
    assert "[Rachat d'un H&R](https://tracker.example/users/moi/transactions/create)" in rachat
    assert "**100 000** points" in rachat and "il manque **55 006**" in rachat
    assert "https://tracker.example/users/moi" in profil


def test_message_rappel_et_solde_suffisant():
    e = embed_avertissements("TOS", 3, "rappel", {**DETAIL, "solde": 12500,
                                                  "rachat_hnr": {"libelle": "Supprimer un H&R", "cost": 5000}})
    assert e["title"] == "Rappel : 3 avertissements toujours actifs sur TOS"
    assert "suffisant pour **2** rachats (3 avertissements à lever)" in e["fields"][1]["value"]


def test_pas_de_lien_de_rachat_sans_article():
    sans_article = {"profil_url": "https://t.example/users/moi", "boutique_lue": True, "solde": 5000}
    assert "Pas d'article de rachat" in texte_rachat(sans_article, 1)
    assert "transactions/create" not in str(embed_avertissements("GF-FREE", 1, "nouveau", sans_article))
    # Boutique non lue (erreur réseau) : rien d'affirmé.
    assert texte_rachat({"solde": 5000}, 1) is None


def test_message_sans_detail():
    e = embed_avertissements("C411", 1, "nouveau", None)
    assert e["title"] == "Avertissement actif : C411" and "fields" not in e


def test_liste_de_torrents_bornee():
    beaucoup = {"avertissements": [
        {"torrent": f"Un.Nom.De.Torrent.Tres.Long.Pour.Remplir.Le.Champ.{i:02d}.MULTi.2160p.UHD.BluRay.x265-GROUPE",
         "url": f"https://tracker.example/torrents/{100000 + i}", "cree_le": "2026-11-17 18:19:37",
         "expire_le": "2026-11-24 18:19:37"} for i in range(10)]}
    e = embed_avertissements("TOS", 10, "critique", beaucoup)
    assert len(e["fields"][0]["value"]) <= 1024


# --- session manuelle : alerte quand le renouvellement automatique n'a pas eu lieu

def test_alerte_d_expiration_sous_24_h_une_fois():
    expiration = T0 + timedelta(days=7)
    assert not session_bientot_expiree(expiration, None, T0)
    # L'ancien préavis (24 à 36 h avant) ne déclenche plus rien : le renouvellement
    # automatique a encore le temps de passer.
    assert not session_bientot_expiree(expiration, None, expiration - timedelta(hours=30))
    assert not session_bientot_expiree(expiration, None, expiration - timedelta(hours=24, seconds=1))
    assert not session_bientot_expiree(expiration, None, expiration - timedelta(hours=24))
    assert session_bientot_expiree(expiration, None, expiration - timedelta(hours=23, minutes=59))
    assert session_bientot_expiree(expiration, None, expiration - timedelta(hours=2))
    # Une seule fois par session déposée.
    assert not session_bientot_expiree(expiration, T0, expiration - timedelta(hours=2))
    assert not session_bientot_expiree(None, None, T0)
    # Dates sans fuseau (SQLite).
    assert session_bientot_expiree(expiration.replace(tzinfo=None), None, expiration - timedelta(hours=2))


def test_alerte_d_expiration_trois_releves_par_jour():
    """Relevés à 8 h, 14 h et 20 h sur 7 jours : une seule alerte, à moins de 24 h de l'échéance."""
    depot = datetime(2026, 11, 18, 9, 30, tzinfo=timezone.utc)
    expiration = depot + timedelta(days=7)
    prevenu, envois = None, []
    releve = datetime(2026, 11, 18, 13, 0, tzinfo=timezone.utc)  # 14 h à Paris
    for n in range(21):
        if releve < expiration and session_bientot_expiree(expiration, prevenu, releve):
            envois.append(releve)
            prevenu = releve
        releve += [6 * H, 12 * H, 6 * H][n % 3]
    assert envois == [datetime(2026, 11, 24, 13, 0, tzinfo=timezone.utc)]
    assert timedelta(0) < expiration - envois[0] < 24 * H


def test_seuil_d_alerte_reglable(monkeypatch):
    expiration = T0 + timedelta(days=7)
    a_30_h = expiration - timedelta(hours=30)
    assert session_bientot_expiree(expiration, None, a_30_h, preavis=timedelta(hours=36))
    monkeypatch.setattr(get_settings(), "session_alerte_heures", 36)
    assert session_bientot_expiree(expiration, None, a_30_h)
    monkeypatch.setattr(get_settings(), "session_alerte_heures", 12)
    assert not session_bientot_expiree(expiration, None, expiration - timedelta(hours=13))


def test_seuil_d_alerte_configuration(monkeypatch):
    monkeypatch.delenv("SESSION_ALERTE_HEURES")
    assert Settings(_env_file=None).session_alerte_heures == 24
    monkeypatch.setenv("SESSION_ALERTE_HEURES", "")
    assert Settings(_env_file=None).session_alerte_heures == 24
    monkeypatch.setenv("SESSION_ALERTE_HEURES", "12.5")
    assert Settings(_env_file=None).session_alerte_heures == 12.5
    monkeypatch.setenv("SESSION_ALERTE_HEURES", "0")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_message_d_expiration_avec_lien():
    expiration = datetime(2026, 11, 25, 9, 45, tzinfo=timezone.utc)
    e = embed_session_bientot_expiree(
        "C411", expiration,
        {"cookie": "__Host-c411_session", "trackboard_url": None, **LIEN_C411},
        maintenant=expiration - timedelta(hours=19, minutes=45))
    assert e["title"] == "Session C411 : renouvellement automatique non effectué"
    assert "renouvellement automatique de la session n'a pas eu lieu" in e["description"]
    assert "**19 h 45**" in e["description"]
    assert "25/11 vers 10 h 45" in e["description"]  # heure de Paris
    assert "[Se reconnecter à C411](https://c411.org/login#trackboard)" in e["description"]
    assert "`__Host-c411_session`" in e["description"]  # repli sans le script
    assert chr(0x2014) not in str(e)


def test_message_d_expiration_sans_lien():
    """Tracker sans lien de reconnexion (Ygg) : même alerte, marche à suivre manuelle, aucun lien."""
    expiration = datetime(2026, 11, 25, 9, 45, tzinfo=timezone.utc)
    for reconnexion in ({"cookie": "__ygg_sess", "trackboard_url": None},
                        {"cookie": "__ygg_sess", "trackboard_url": None, "lien_reconnexion": None}):
        e = embed_session_bientot_expiree("YGG", expiration, reconnexion,
                                          maintenant=expiration - timedelta(minutes=40))
        assert "**40 min**" in e["description"] and "`__ygg_sess`" in e["description"]
        assert "](" not in e["description"] and "http" not in e["description"]
        assert "script" not in e["description"]


def test_message_d_expiration_echeance_depassee():
    expiration = datetime(2026, 11, 25, 9, 45, tzinfo=timezone.utc)
    e = embed_session_bientot_expiree("C411", expiration, {"cookie": "c", **LIEN_C411},
                                      maintenant=expiration + timedelta(hours=1))
    assert "est dépassée" in e["description"] and "expire dans" not in e["description"]


def test_lien_de_reconnexion_declare_par_le_tracker():
    assert C411Scraper.SESSION_COOKIE["lien_reconnexion"] == "https://c411.org/login#trackboard"
    assert "lien_reconnexion" not in YggScraper.SESSION_COOKIE
    assert BaseScraper.SESSION_COOKIE is None


def test_reconnexion_transmet_le_lien(monkeypatch):
    from app.scrapers import routes

    def scraper(classe, nom):
        return classe(ScraperConfig(name=nom, login_url="https://site.example/login",
                                    profile_url_template="https://site.example/me"))

    assert routes._reconnexion(scraper(C411Scraper, "C411"))["lien_reconnexion"] == LIEN_C411["lien_reconnexion"]
    assert routes._reconnexion(scraper(YggScraper, "YGG"))["lien_reconnexion"] is None
