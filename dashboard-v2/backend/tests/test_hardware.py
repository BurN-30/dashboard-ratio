"""Tests pour le monitoring hardware."""
import pytest
from httpx import AsyncClient
from app.hardware.manager import HardwareManager, HardwareData


class TestHardwareManager:
    """Tests du gestionnaire hardware."""

    def test_initial_state(self):
        mgr = HardwareManager()
        assert mgr.is_agent_connected is False
        assert mgr.clients == {}
        assert mgr.latest_data.agent_connected is False

    def test_get_latest_empty(self):
        mgr = HardwareManager()
        data = mgr.get_latest()
        assert data["agent_connected"] is False
        assert data["cpu"] == {}
        assert data["ram"] == {}
        assert data["storage"] == []

    def test_format_data(self):
        mgr = HardwareManager()
        mgr.latest_data = HardwareData(
            cpu={"usage": 45.0, "temp": 62.0},
            ram={"used_percent": 70.5},
            gpu={"name": "RTX 3080"},
            storage=[{"device": "C:", "percent": 55}],
            network={"download": 10.5},
            processes=[],
            os="Windows 11",
            hostname="PC-NATHAN",
            uptime="5 j 3 h",
            timestamp="2026-02-07T10:00:00",
            agent_connected=True,
        )
        data = mgr._format_data()
        assert data["cpu"]["usage"] == 45.0
        assert data["ram"]["used_percent"] == 70.5
        assert data["os"] == "Windows 11"
        assert data["agent_connected"] is True


class TestHardwareRoutes:
    """Tests des routes /hardware/*."""

    async def test_hardware_status(self, client: AsyncClient):
        """GET /hardware/status est public."""
        resp = await client.get("/hardware/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "agent_connected" in data
        assert "clients_count" in data

    async def test_hardware_stats_requires_auth(self, client: AsyncClient):
        resp = await client.get("/hardware/stats")
        assert resp.status_code in (401, 403)

    async def test_hardware_stats_authenticated(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get("/hardware/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "agent_connected" in data


class TestHardwareData:
    """Tests du dataclass HardwareData."""

    def test_defaults(self):
        data = HardwareData()
        assert data.cpu == {}
        assert data.ram == {}
        assert data.storage == []
        assert data.agent_connected is False
        assert data.timestamp is None

    def test_with_values(self):
        data = HardwareData(
            cpu={"usage": 50},
            ram={"used_percent": 65},
            agent_connected=True,
        )
        assert data.cpu["usage"] == 50
        assert data.agent_connected is True
