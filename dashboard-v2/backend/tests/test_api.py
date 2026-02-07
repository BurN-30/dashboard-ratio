"""Tests pour les routes API (stats, history, summary)."""
import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """Tests des endpoints de sante."""

    async def test_root(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["version"] == "2.0.0"

    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class TestStats:
    """Tests du endpoint /api/stats."""

    async def test_stats_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/stats")
        assert resp.status_code in (401, 403)

    async def test_stats_empty_db(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "_timestamp" in data

    async def test_stats_with_data(
        self, client: AsyncClient, auth_headers: dict, seeded_db
    ):
        resp = await client.get("/api/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()

        # Verifie qu'on a les 3 trackers
        assert "Generation-Free" in data
        assert "Sharewood" in data
        assert "TheOldSchool" in data

        # Verifie les valeurs GF (le plus recent)
        gf = data["Generation-Free"]
        assert gf["ratio"] == "2.5"
        assert gf["buffer"] == "150 Go"
        assert gf["vol_upload"] == "500 Go"
        assert gf["count_seed"] == "42"

    async def test_stats_returns_latest_only(
        self, client: AsyncClient, auth_headers: dict, seeded_db
    ):
        """Verifie qu'on recupere seulement le dernier snapshot par tracker."""
        resp = await client.get("/api/stats", headers=auth_headers)
        data = resp.json()
        # GF a 2 entrees (ratio 2.3 et 2.5), on doit avoir le plus recent (2.5)
        assert data["Generation-Free"]["ratio"] == "2.5"


class TestHistory:
    """Tests du endpoint /api/history."""

    async def test_history_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/history")
        assert resp.status_code in (401, 403)

    async def test_history_empty_db(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/history", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_history_with_data(
        self, client: AsyncClient, auth_headers: dict, seeded_db
    ):
        resp = await client.get("/api/history", headers=auth_headers)
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) >= 2  # Au moins 2 snapshots (2 dates differentes)
        # Verifie le tri chronologique
        timestamps = [s["_timestamp"] for s in history]
        assert timestamps == sorted(timestamps)

    async def test_history_filter_by_tracker(
        self, client: AsyncClient, auth_headers: dict, seeded_db
    ):
        resp = await client.get(
            "/api/history?tracker=Generation-Free", headers=auth_headers
        )
        assert resp.status_code == 200
        history = resp.json()
        # Tous les snapshots doivent contenir GF
        for snapshot in history:
            assert "Generation-Free" in snapshot

    async def test_history_days_param(
        self, client: AsyncClient, auth_headers: dict, seeded_db
    ):
        resp = await client.get("/api/history?days=1", headers=auth_headers)
        assert resp.status_code == 200

    async def test_history_days_validation(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get("/api/history?days=0", headers=auth_headers)
        assert resp.status_code == 422  # Validation: ge=1

        resp = await client.get("/api/history?days=999", headers=auth_headers)
        assert resp.status_code == 422  # Validation: le=365


class TestTrackerStats:
    """Tests du endpoint /api/stats/{tracker_name}."""

    async def test_tracker_stats(
        self, client: AsyncClient, auth_headers: dict, seeded_db
    ):
        resp = await client.get(
            "/api/stats/Generation-Free", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tracker"] == "Generation-Free"
        assert data["count"] == 2  # 2 entrees GF dans le seed

    async def test_tracker_stats_unknown(
        self, client: AsyncClient, auth_headers: dict, seeded_db
    ):
        resp = await client.get("/api/stats/UnknownTracker", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


class TestSummary:
    """Tests du endpoint /api/summary."""

    async def test_summary_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/summary")
        assert resp.status_code in (401, 403)

    async def test_summary_with_data(
        self, client: AsyncClient, auth_headers: dict, seeded_db
    ):
        resp = await client.get("/api/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["trackers_count"] == 3  # GF, SW, TOS
        assert data["total_records"] == 4  # 4 entrees dans le seed
        assert data["last_update"] is not None
