"""
@file test_auth_sso_only.py
@brief Unit tests for SSO-only enforcement: auth rejection, SSO unaffected, toggle API.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user, get_db

MSG = "Single sign-on only: password login is disabled"
GUARD = "app.services.auth.sso_only.is_sso_only"


@pytest.fixture
def db_override(test_app):
    """@brief Override get_db with a mock session."""
    session = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: session
    yield session
    test_app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def admin_override(test_app):
    """@brief Override get_current_user with an admin."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = "admin"
    test_app.dependency_overrides[get_current_user] = lambda: user
    yield user
    test_app.dependency_overrides.pop(get_current_user, None)


def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestPasswordAuthRejected:
    """@brief Password and magic-link auth return 403 when sso_only is on."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("path", "body"),
        [
            ("/api/v1/auth/login", {"email": "a@b.co", "password": "Passw0rd!xyz"}),
            (
                "/api/v1/auth/register",
                {
                    "email": "a@b.co",
                    "username": "abc",
                    "password": "Passw0rd!xyz1",
                    "display_name": "A",
                },
            ),
            ("/api/v1/auth/magic-link/request", {"email": "a@b.co"}),
        ],
    )
    async def test_rejected_with_403(self, test_app, db_override, path, body):
        with patch(GUARD, AsyncMock(return_value=True)):
            async with _client(test_app) as c:
                resp = await c.post(path, json=body)
        assert resp.status_code == 403
        assert resp.json()["error"]["message"] == MSG

    @pytest.mark.asyncio
    async def test_login_not_blocked_when_off(self, test_app, db_override):
        """Guard off: login proceeds to normal credential check (401, not 403)."""
        with (
            patch(GUARD, AsyncMock(return_value=False)),
            patch(
                "app.services.auth_service.UserRepository.find_by_email",
                AsyncMock(return_value=None),
            ),
        ):
            async with _client(test_app) as c:
                resp = await c.post(
                    "/api/v1/auth/login",
                    json={"email": "a@b.co", "password": "Passw0rd!xyz"},
                )
        assert resp.status_code == 401


class TestSsoStillWorks:
    """@brief SSO paths are not gated by the toggle."""

    @pytest.mark.asyncio
    async def test_config_reports_local_auth_disabled(self, test_app, db_override):
        with (
            patch(GUARD, AsyncMock(return_value=True)),
            patch(
                "app.services.oauth.provider_manager.ProviderManager.get_enabled_providers",
                AsyncMock(return_value=[]),
            ),
        ):
            async with _client(test_app) as c:
                resp = await c.get("/api/v1/auth/config")
        assert resp.status_code == 200
        body = resp.json()
        assert body["local_auth_enabled"] is False
        assert body["sso_only"] is True

    @pytest.mark.asyncio
    async def test_oauth_login_route_not_guarded(self):
        """OAuth routes never call the guard."""
        import inspect

        import app.api.v1.oauth as oauth_api

        assert "sso_only" not in inspect.getsource(oauth_api)


class TestToggleApi:
    """@brief PATCH /api/v1/admin/settings/sso-only."""

    @pytest.mark.asyncio
    async def test_enable_succeeds_with_provider(self, test_app, db_override, admin_override):
        with (
            patch(
                "app.services.auth.sso_only.count_enabled_providers",
                AsyncMock(return_value=1),
            ),
            patch("app.services.auth.sso_only.write_flag", AsyncMock()) as write,
        ):
            async with _client(test_app) as c:
                resp = await c.patch("/api/v1/admin/settings/sso-only", json={"enabled": True})
        assert resp.status_code == 200
        assert resp.json()["sso_only"] is True
        assert "warning" in resp.json()
        write.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_enable_rejected_without_provider(self, test_app, db_override, admin_override):
        with (
            patch(
                "app.services.auth.sso_only.count_enabled_providers",
                AsyncMock(return_value=0),
            ),
            patch("app.services.auth.sso_only.write_flag", AsyncMock()) as write,
        ):
            async with _client(test_app) as c:
                resp = await c.patch("/api/v1/admin/settings/sso-only", json={"enabled": True})
        assert resp.status_code == 422
        assert "OIDC provider" in resp.json()["error"]["message"]
        write.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_disable_needs_no_provider(self, test_app, db_override, admin_override):
        with patch("app.services.auth.sso_only.write_flag", AsyncMock()):
            async with _client(test_app) as c:
                resp = await c.patch("/api/v1/admin/settings/sso-only", json={"enabled": False})
        assert resp.status_code == 200
        assert resp.json()["sso_only"] is False

    @pytest.mark.asyncio
    async def test_non_admin_forbidden(self, test_app, db_override):
        user = MagicMock()
        user.id = uuid.uuid4()
        user.role = "member"
        test_app.dependency_overrides[get_current_user] = lambda: user
        try:
            async with _client(test_app) as c:
                resp = await c.patch("/api/v1/admin/settings/sso-only", json={"enabled": True})
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 403
