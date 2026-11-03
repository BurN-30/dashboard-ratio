"""Tests du parseur TR4KER (reponse /api/me/stats)."""
import pytest

from app.scrapers.tr4ker import format_bytes, format_seedtime, parse_stats

EXEMPLE = {
    "summary": {"uploaded": 4410358112030, "downloaded": 2167716117199,
                "bonus_upload": 42062762213376, "bonus_download": 1073741824,
                "money": 1036093, "ratio_warning": False},
    "statistics": {"torrents_completed": 2283, "torrents_seeding": 174,
                   "total_seedtime_seconds": 5314092813, "uploaded_last_24h": 14441021016,
                   "uploaded_last_7d": 0, "uploaded_last_30d": 404122753189,
                   "downloaded_last_24h": 0, "downloaded_last_7d": 0,
                   "downloaded_last_30d": 513688586539},
}


def test_ratio_compte_le_bonus_comme_le_site():
    c = parse_stats(EXEMPLE)
    assert c["ratio"] == "21.43"
    assert c["vol_upload"] == "46.47 To"
    assert c["vol_download"] == "2.17 To"
    assert c["buffer"] == "44.30 To"


def test_compteurs_et_points():
    c = parse_stats(EXEMPLE)
    assert c["count_seed"] == "174"
    assert c["count_downloaded"] == "2283"
    assert c["points_bonus"] == "1 036 093"
    assert c["warnings_active"] == "0"
    assert c["seed_time_total"] == "168a 6mo"
    assert c["raw_data"]["upload_30j"] == "404.12 Go"


def test_avertissement_de_ratio():
    d = {**EXEMPLE, "summary": {**EXEMPLE["summary"], "ratio_warning": True}}
    assert parse_stats(d)["warnings_active"] == "1"


@pytest.mark.parametrize("payload", [{}, {"summary": {}}, {"summary": {"uploaded": 0, "downloaded": 0}}])
def test_reponse_inattendue_leve_une_erreur(payload):
    with pytest.raises(ValueError):
        parse_stats(payload)


def test_formats():
    assert format_bytes(0) == "0"
    assert format_bytes(-2e9) == "-2.00 Go"
    assert format_seedtime(0) == "0"
    assert format_seedtime(3 * 86400 + 7200) == "3j 2h"
    assert format_seedtime(45 * 86400) == "1mo 15j"
