"""Tests des paliers de boutique et de l'estimation d'upload achetable."""
from app.scrapers.boutique import (
    estimer_gib, format_gib, parse_paliers_unit3d, paliers_tr4ker, points_en_entier, upload_achetable,
)

PAGE_UNIT3D = "Objet\tCost\tÉchange\n10 GiB Upload\t2 500\nEchanger\n100 GiB Upload\t20 000\n500 GiB Upload\t80 000\nGuide Upload\n"


def test_parse_unit3d_libelle_et_prix_sur_la_meme_ligne():
    assert parse_paliers_unit3d(PAGE_UNIT3D) == [
        {"gib": 10.0, "cost": 2500}, {"gib": 100.0, "cost": 20000}, {"gib": 500.0, "cost": 80000},
    ]
    assert parse_paliers_unit3d("1 TiB Upload\t150000") == [{"gib": 1024.0, "cost": 150000}]


def test_paliers_tr4ker():
    items = [{"price": 8000, "bonus_bytes": 1099511627776}, {"id": "freeleech", "price": 300}]
    assert paliers_tr4ker(items) == [{"gib": 1024.0, "cost": 8000}]


def test_points_en_entier():
    assert points_en_entier("9 040 535 G★") == 9040535
    assert points_en_entier("1,917,419.50") == 1917419
    assert points_en_entier("2 752 312") == 2752312
    assert points_en_entier(None) == 0


def test_estimation_achete_d_abord_le_meilleur_prix_au_go():
    paliers = parse_paliers_unit3d(PAGE_UNIT3D)
    # 170 000 = 2 x 500 Go (160 000) + reste 10 000 -> 0 x 100 Go, 4 x 10 Go
    assert estimer_gib(170000, paliers) == 1040.0
    assert estimer_gib(0, paliers) == 0


def test_format_et_texte_final():
    assert format_gib(11880) == "11.6 To"
    assert format_gib(580) == "580 Go"
    paliers = {"X": [{"gib": 1024.0, "cost": 8000}]}
    assert upload_achetable("X", "16 000", paliers) == "2.0 To"
    assert upload_achetable("Y", "16 000", paliers) is None
