"""Tests du parseur YggReborn (page /account/). Chiffres inventés."""
import pytest

from app.scrapers.ygg import parse_compte, taille_en_octets

PAGE = """MON COMPTE
Bienvenue, membre
STATISTIQUES TRACKER
120.50 Go
UPLOAD
100.25 Go
DOWNLOAD
40.00 Go
FREELEECH DL
1.20
RATIO
STATUT UTILISATEUR
Aucun bonus
—
SCORE
3
UPLOADS
0
VÉRIFIÉS
"""


def test_parse_compte():
    c = parse_compte(PAGE)
    assert c["ratio"] == "1.20"
    assert c["vol_upload"] == "120.50 Go"
    assert c["vol_download"] == "100.25 Go"
    assert c["buffer"] == "20.25 Go"
    assert c["points_bonus"] == "0"
    assert c["raw_data"] == {"freeleech_dl": "40.00 Go", "uploads": "3"}


def test_score_numerique():
    c = parse_compte(PAGE.replace("—\nSCORE", "1 250\nSCORE"))
    assert c["points_bonus"] == "1 250"


def test_page_changee_leve_une_erreur():
    with pytest.raises(ValueError):
        parse_compte("Connexion\nMot de passe\n")


def test_tailles():
    assert taille_en_octets("1.5 To") == 1.5e12
    assert taille_en_octets("2 Gio") == 2 * 1024 ** 3
    assert taille_en_octets("—") is None
