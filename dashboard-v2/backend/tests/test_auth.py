"""Tests pour l'authentification JWT."""
import pytest
from httpx import AsyncClient


class TestLogin:
    """Tests du endpoint /auth/login."""

    async def test_login_success(self, client: AsyncClient):
        resp = await client.post("/auth/login", json={"password": "testpass"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "access_token" in data["token"]
        assert data["token"]["token_type"] == "bearer"
        assert data["token"]["expires_in"] > 0

    async def test_login_wrong_password(self, client: AsyncClient):
        resp = await client.post("/auth/login", json={"password": "wrong"})
        assert resp.status_code == 401

    async def test_login_empty_password(self, client: AsyncClient):
        resp = await client.post("/auth/login", json={"password": ""})
        assert resp.status_code == 401

    async def test_login_missing_password(self, client: AsyncClient):
        resp = await client.post("/auth/login", json={})
        assert resp.status_code == 422  # Validation error

    async def test_login_remember_me(self, client: AsyncClient):
        resp = await client.post(
            "/auth/login",
            json={"password": "testpass", "remember_me": True}
        )
        assert resp.status_code == 200
        data = resp.json()
        # remember_me = 30 jours = 2592000 secondes
        assert data["token"]["expires_in"] == 2592000


class TestLogout:
    """Tests du endpoint /auth/logout."""

    async def test_logout(self, client: AsyncClient):
        resp = await client.post("/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestMe:
    """Tests du endpoint /auth/me."""

    async def test_me_authenticated(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"] == "admin"
        assert data["authenticated"] is True

    async def test_me_no_token(self, client: AsyncClient):
        resp = await client.get("/auth/me")
        assert resp.status_code in (401, 403)  # HTTPBearer returns 403 when missing

    async def test_me_invalid_token(self, client: AsyncClient):
        headers = {"Authorization": "Bearer invalid-token-here"}
        resp = await client.get("/auth/me", headers=headers)
        assert resp.status_code == 401


class TestRefresh:
    """Tests du endpoint /auth/refresh."""

    async def test_refresh_token(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post("/auth/refresh", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "access_token" in data["token"]

    async def test_refresh_no_token(self, client: AsyncClient):
        resp = await client.post("/auth/refresh")
        assert resp.status_code in (401, 403)
