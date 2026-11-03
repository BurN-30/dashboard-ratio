"""Tests du scraper C411 (API JSON et boutique Nuxt). Chiffres inventés."""
import json

import pytest

from app.scrapers.c411 import paliers_boutique, parse_me

ME = {"authenticated": True, "user": {
    "uploaded": 3_000_000_000_000, "downloaded": 1_000_000_000_000, "uploadCredit": 500_000_000_000,
    "downloadCredit": 0, "ratio": 3.0, "warnings": 0, "ratioWarning": None,
    "minRatioForDownload": 0.8, "canDownload": True}}


def test_parse_me():
    c = parse_me(ME, {"balance": 12345})
    assert c["ratio"] == "3.00"
    assert c["vol_upload"] == "3.00 To"
    assert c["vol_download"] == "1.00 To"
    assert c["buffer"] == "2.00 To"
    assert c["points_bonus"] == "12 345"
    assert c["warnings_active"] == "0"
    assert c["raw_data"]["credit_upload"] == "500.00 Go"


def test_avertissement_de_ratio_compte():
    me = {"authenticated": True, "user": {**ME["user"], "ratioWarning": {"since": "x"}}}
    assert parse_me(me, None)["warnings_active"] == "1"


def test_session_expiree():
    with pytest.raises(PermissionError):
        parse_me({"authenticated": False}, None)


def test_paliers_boutique_charge_utile_nuxt():
    # Format devalue : les valeurs des objets sont des index dans le tableau.
    donnees = [
        ["ShallowReactive", 1],
        {"items": 2},
        [3, 7],
        {"slug": 4, "category": 5, "price": 6, "payload": 10},
        "go_50", "go_credit", 50,
        {"slug": 8, "category": 9, "price": 6, "payload": 12},
        "pack_c411", "pack",
        {"bytes": 11}, 53687091200,
        {"pack_slug": 8},
    ]
    html = f'<html><script type="application/json" id="__NUXT_DATA__" data-ssr="true">{json.dumps(donnees)}</script></html>'
    assert paliers_boutique(html) == [{"gib": 50.0, "cost": 50}]
    assert paliers_boutique("<html></html>") == []
