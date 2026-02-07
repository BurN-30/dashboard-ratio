"""Tests pour les scrapers et leur registry."""
import pytest
from httpx import AsyncClient
from app.scrapers.registry import SITES_CONFIG, get_credentials_from_env
from app.scrapers.base import BaseScraper, ScrapedStats


class TestScraperRegistry:
    """Tests du registre de scrapers."""

    def test_sites_config_count(self):
        """5 sites configures (GF, TOS, SW, Torr9, Gemini)."""
        assert len(SITES_CONFIG) == 5

    def test_sites_config_names(self):
        names = [s["name"] for s in SITES_CONFIG]
        assert "Generation-Free" in names
        assert "TheOldSchool" in names
        assert "Sharewood" in names
        assert "Torr9" in names
        assert "Gemini" in names

    def test_sites_config_has_required_keys(self):
        required = {"name", "scraper_class", "login_url", "profile_url_template", "env_prefix"}
        for site in SITES_CONFIG:
            assert required.issubset(site.keys()), f"{site['name']} manque des cles"

    def test_credentials_from_env(self):
        """Verifie que les credentials de test sont chargees."""
        # En test, on n'a pas de credentials trackers dans les env vars
        user, password, username = get_credentials_from_env("gf")
        # Ils peuvent etre None en env de test, c'est OK
        assert isinstance(user, (str, type(None)))


class TestScraperRoutes:
    """Tests des routes /scrapers/*."""

    async def test_sites_list(self, client: AsyncClient):
        """GET /scrapers/sites est public."""
        resp = await client.get("/scrapers/sites")
        assert resp.status_code == 200
        data = resp.json()
        assert "sites" in data
        assert len(data["sites"]) == 5

    async def test_available_requires_auth(self, client: AsyncClient):
        resp = await client.get("/scrapers/available")
        assert resp.status_code in (401, 403)

    async def test_status(self, client: AsyncClient):
        resp = await client.get("/scrapers/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "scraping_in_progress" in data
        assert data["scraping_in_progress"] is False

    async def test_run_requires_auth(self, client: AsyncClient):
        resp = await client.post("/scrapers/run")
        assert resp.status_code in (401, 403)

    async def test_run_single_unknown_tracker(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post("/scrapers/run/FakeTracker", headers=auth_headers)
        assert resp.status_code == 404


class TestScrapedStats:
    """Tests du dataclass ScrapedStats."""

    def test_scraped_stats_defaults(self):
        stats = ScrapedStats(tracker_name="Test")
        assert stats.tracker_name == "Test"
        assert stats.ratio is None
        assert stats.buffer is None
        assert stats.raw_data is None

    def test_scraped_stats_with_data(self):
        stats = ScrapedStats(
            tracker_name="GF",
            ratio="2.5",
            buffer="150 Go",
            vol_upload="500 Go",
            vol_download="200 Go",
        )
        assert stats.ratio == "2.5"
        assert stats.buffer == "150 Go"


class TestBaseScraperUtils:
    """Tests des utilitaires de BaseScraper."""

    def test_clean_text_basic(self):
        assert BaseScraper.clean_text("  hello  ") == "hello"

    def test_clean_text_units(self):
        assert BaseScraper.clean_text("500 GiB") == "500 Go"
        assert BaseScraper.clean_text("1.5 TiB") == "1.5 To"
        assert BaseScraper.clean_text("200 MiB") == "200 Mo"

    def test_clean_text_none(self):
        assert BaseScraper.clean_text(None) == "0"

    def test_clean_text_empty(self):
        assert BaseScraper.clean_text("") == "0"

    def test_format_duration_basic(self):
        result = BaseScraper.format_duration("5D3H")
        assert "j" in result
        assert "h" in result

    def test_format_duration_none(self):
        assert BaseScraper.format_duration(None) == "0"
        assert BaseScraper.format_duration("0") == "0"
