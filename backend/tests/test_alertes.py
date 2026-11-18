"""Alertes Discord : anti-répétition (échecs, avertissements, session) et texte des messages."""
from datetime import datetime, timedelta, timezone

from app.notifications import (
    decider_alerte_avertissements, decider_alerte_echec, embed_avertissements, embed_echec,
    embed_session_bientot_expiree, session_bientot_expiree, texte_rachat,
)

T0 = datetime(2026, 11, 18, 13, 0, 30, tzinfo=timezone.utc)
H = timedelta(hours=1)


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


# --- session manuelle : rappel avant l'expiration

def test_rappel_d_expiration_une_fois():
    expiration = T0 + timedelta(days=7)
    assert not session_bientot_expiree(expiration, None, T0)
    assert not session_bientot_expiree(expiration, None, expiration - timedelta(hours=40))
    assert session_bientot_expiree(expiration, None, expiration - timedelta(hours=30))
    assert not session_bientot_expiree(expiration, T0, expiration - timedelta(hours=30))
    assert not session_bientot_expiree(None, None, T0)


def test_message_d_expiration():
    e = embed_session_bientot_expiree("C411", datetime(2026, 11, 25, 9, 45, tzinfo=timezone.utc),
                                      {"cookie": "__Host-c411_session", "trackboard_url": None})
    assert "25/11 vers 10 h 45" in e["title"]  # heure de Paris
    assert "`__Host-c411_session`" in e["description"]
