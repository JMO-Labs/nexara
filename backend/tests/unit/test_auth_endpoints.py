"""
@file test_auth_endpoints.py
@brief Unit tests for auth API endpoints using httpx AsyncClient.

Tests exercise the route layer with mocked service dependencies,
verifying status codes, response shapes, and cookie handling.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.core.security import hash_password


def _make_settings() -> Settings:
    """@brief Test settings with HS256 for speed."""
    return Settings(
        SECRET_KEY="test-auth-endpoints",
        JWT_ALGORITHM="HS256",
        WAF_ENABLED=False,
        ENABLE_METRICS=False,
    )


def _mock_user(**overrides) -> MagicMock:
    """@brief Build a mock User."""
    user = MagicMock()
    user.id = overrides.get("id", uuid.uuid4())
    user.community_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user.email = overrides.get("email", "test@example.com")
    user.username = overrides.get("username", "testuser")
    user.display_name = overrides.get("display_name", "Test User")
    user.password_hash = overrides.get("password_hash", hash_password("valid-password1"))
    user.role = overrides.get("role", "member")
    user.is_active = True
    user.totp_enabled = overrides.get("totp_enabled", False)
    user.totp_secret = overrides.get("totp_secret", None)
    user.email_verified = True
    user.avatar_url = None
    user.bio = None
    user.title = None
    user.location = None
    user.website_url = None
    user.birthday = None
    user.storage_used = 0
    user.storage_quota = 1073741824
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.last_seen_at = None
    user.deleted_at = None
    return user


class TestAuthConfigEndpoint:
    """@brief GET /api/v1/auth/config tests."""

    @pytest.mark.asyncio
    async def test_config_oidc_disabled_when_client_id_empty(self, test_app):
        """When OIDC_CLIENT_ID is not set, oidc_enabled is False."""
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/auth/config")

        assert resp.status_code == 200
        data = resp.json()
        assert data["oidc_enabled"] is False
        assert "registration_enabled" in data

    @pytest.mark.asyncio
    async def test_config_oidc_enabled_when_client_id_set(self, test_app):
        """When OIDC_CLIENT_ID is set, oidc_enabled is True."""
        oidc_settings = Settings(
            SECRET_KEY="test-auth-endpoints",
            JWT_ALGORITHM="HS256",
            WAF_ENABLED=False,
            ENABLE_METRICS=False,
            OIDC_CLIENT_ID="my-oidc-client",
            OIDC_CLIENT_SECRET="secret",
        )

        def _oidc_settings():
            return oidc_settings

        test_app.dependency_overrides[get_settings] = _oidc_settings
        try:
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/auth/config")

            assert resp.status_code == 200
            data = resp.json()
            assert data["oidc_enabled"] is True
            assert data["registration_enabled"] is True
        finally:
            test_app.dependency_overrides.pop(get_settings, None)


class TestRegisterEndpoint:
    """@brief POST /api/v1/auth/register tests."""

    @pytest.mark.asyncio
    async def test_register_success(self, test_app):
        mock_result = {
            "access_token": "jwt-token",
            "expires_in": 900,
            "raw_refresh_token": "refresh-hex",
            "requires_2fa": False,
        }

        with patch("app.api.v1.auth.AuthService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.register.return_value = mock_result
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": "new@example.com",
                        "username": "newuser",
                        "password": "strong-pass-12",
                        "display_name": "New User",
                    },
                )

            assert resp.status_code == 201
            data = resp.json()
            assert data["access_token"] == "jwt-token"
            assert "set-cookie" in resp.headers

    @pytest.mark.asyncio
    async def test_register_validation_error(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "not-valid",
                    "username": "ab",
                    "password": "short",
                    "display_name": "",
                },
            )

        assert resp.status_code == 422


class TestLoginEndpoint:
    """@brief POST /api/v1/auth/login tests."""

    @pytest.mark.asyncio
    async def test_login_success(self, test_app):
        mock_result = {
            "access_token": "jwt-token",
            "expires_in": 900,
            "raw_refresh_token": "refresh-hex",
            "requires_2fa": False,
        }

        with patch("app.api.v1.auth.AuthService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.login.return_value = mock_result
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": "user@example.com",
                        "password": "valid-password1",
                    },
                )

            assert resp.status_code == 200
            data = resp.json()
            assert data["access_token"]

    @pytest.mark.asyncio
    async def test_login_2fa_required(self, test_app):
        mock_result = {
            "requires_2fa": True,
            "two_factor_token": "pending-jwt",
        }

        with patch("app.api.v1.auth.AuthService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.login.return_value = mock_result
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": "user@example.com",
                        "password": "valid-password1",
                    },
                )

            assert resp.status_code == 200
            data = resp.json()
            assert data["requires_2fa"] is True

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, test_app):
        from app.core.exceptions import AuthenticationError

        with patch("app.api.v1.auth.AuthService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.login.side_effect = AuthenticationError(message="Invalid email or password")
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": "user@example.com",
                        "password": "wrong-password",
                    },
                )

            assert resp.status_code == 401


class TestRefreshEndpoint:
    """@brief POST /api/v1/auth/refresh tests."""

    @pytest.mark.asyncio
    async def test_refresh_without_cookie_returns_401(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/refresh")

        assert resp.status_code == 401


class TestLogoutEndpoint:
    """@brief POST /api/v1/auth/logout tests."""

    @pytest.mark.asyncio
    async def test_logout_without_cookie_still_succeeds(self, test_app):
        """Logout without a cookie gracefully returns 200 to prevent enumeration."""
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/logout")

        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data


class TestJWKSEndpoint:
    """@brief GET /.well-known/jwks.json tests."""

    @pytest.mark.asyncio
    async def test_jwks_returns_keys(self, test_app):
        with patch("app.core.security.get_jwks", return_value={"keys": []}):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/.well-known/jwks.json")

            assert resp.status_code == 200
            data = resp.json()
            assert "keys" in data
