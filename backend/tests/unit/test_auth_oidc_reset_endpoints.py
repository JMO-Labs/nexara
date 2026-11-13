"""
@file test_auth_oidc_reset_endpoints.py
@brief Unit tests for deprecated OIDC redirects, JWKS and password-reset routes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_db

_MGR = "app.services.oauth.provider_manager.ProviderManager"


def _client(app) -> AsyncClient:
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _manager(providers):
    mgr = MagicMock()
    mgr.get_enabled_providers = AsyncMock(return_value=providers)
    return MagicMock(return_value=mgr)


def _provider(slug="corp"):
    p = MagicMock()
    p.slug = slug
    return p


class TestOidcDeprecated:
    """@brief /auth/oidc/login and /auth/oidc/callback."""

    @pytest.mark.asyncio
    async def test_login_redirects_to_first_provider(self, test_app):
        with patch(_MGR, _manager([_provider("corp")])):
            async with _client(test_app) as c:
                r = await c.get("/api/v1/auth/oidc/login", follow_redirects=False)
        assert r.status_code == 307
        assert r.headers["location"] == "/api/v1/oauth/corp/login"

    @pytest.mark.asyncio
    async def test_login_without_providers_is_401(self, test_app):
        with patch(_MGR, _manager([])):
            async with _client(test_app) as c:
                r = await c.get("/api/v1/auth/oidc/login", follow_redirects=False)
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_callback_redirects_with_code_and_state(self, test_app):
        with patch(_MGR, _manager([_provider("corp")])):
            async with _client(test_app) as c:
                r = await c.get(
                    "/api/v1/auth/oidc/callback?code=abc&state=xyz", follow_redirects=False
                )
        assert r.status_code == 307
        assert r.headers["location"] == "/api/v1/oauth/corp/callback?code=abc&state=xyz"

    @pytest.mark.asyncio
    async def test_callback_without_providers_is_401(self, test_app):
        with patch(_MGR, _manager([])):
            async with _client(test_app) as c:
                r = await c.get("/api/v1/auth/oidc/callback?code=a&state=b", follow_redirects=False)
        assert r.status_code == 401


class TestJwks:
    """@brief /auth/.well-known/jwks.json delegates to get_jwks."""

    @pytest.mark.asyncio
    async def test_jwks_returns_payload(self, test_app):
        with patch("app.api.v1.auth_oidc.get_jwks", return_value={"keys": []}):
            async with _client(test_app) as c:
                r = await c.get("/api/v1/auth/.well-known/jwks.json")
        assert r.status_code == 200
        assert r.json() == {"keys": []}


class TestPasswordResetRoutes:
    """@brief /auth/password-reset/{request,confirm}."""

    @pytest.mark.asyncio
    async def test_request_returns_generic_message(self, test_app):
        svc = MagicMock()
        svc.request_password_reset = AsyncMock()
        with patch("app.api.v1.auth_password_reset.AuthService", return_value=svc):
            async with _client(test_app) as c:
                r = await c.post("/api/v1/auth/password-reset/request", json={"email": "a@b.com"})
        assert r.status_code == 200
        assert "reset link" in r.json()["message"]
        svc.request_password_reset.assert_awaited_once_with("a@b.com")

    @pytest.mark.asyncio
    async def test_confirm_resets_password(self, test_app):
        svc = MagicMock()
        svc.reset_password = AsyncMock()
        with patch("app.api.v1.auth_password_reset.AuthService", return_value=svc):
            async with _client(test_app) as c:
                r = await c.post(
                    "/api/v1/auth/password-reset/confirm",
                    json={"token": "tok", "new_password": "a-long-password-1"},
                )
        assert r.status_code == 200
        assert "reset successfully" in r.json()["message"]
        svc.reset_password.assert_awaited_once_with("tok", "a-long-password-1")
