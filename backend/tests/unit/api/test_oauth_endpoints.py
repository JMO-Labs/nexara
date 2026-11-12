"""
@file test_oauth_endpoints.py
@brief Unit tests for public OAuth API endpoints.

Tests GET /oauth/{slug}/login, GET /oauth/{slug}/callback,
POST /oauth/exchange, and updated GET /auth/config.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


class TestOAuthLoginEndpoint:
    """@brief GET /api/v1/oauth/{slug}/login tests."""

    @pytest.mark.asyncio
    async def test_login_returns_302_redirect(self, test_app):
        """GET /oauth/{slug}/login returns 302 redirect to provider."""
        mock_provider = MagicMock()
        mock_provider.slug = "oidc"
        mock_provider.authorization_endpoint = "https://auth.example.com/authorize"
        mock_provider.scopes = "openid profile email"

        with (
            patch("app.api.v1.oauth.ProviderManager") as mock_manager_cls,
            patch("app.api.v1.oauth.OAuthFlow") as mock_flow_cls,
        ):
            mock_manager = AsyncMock()
            mock_manager.get_provider = AsyncMock(return_value=mock_provider)
            mock_manager_cls.return_value = mock_manager

            mock_flow = MagicMock()
            mock_flow.build_authorize_url.return_value = (
                "https://auth.example.com/authorize?client_id=...",
                "state-123",
                "verifier-456",
            )
            mock_flow_cls.return_value = mock_flow

            transport = ASGITransport(app=test_app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
                follow_redirects=False,
            ) as client:
                resp = await client.get("/api/v1/oauth/oidc/login")

            assert resp.status_code == 302
            assert "location" in resp.headers
            assert "auth.example.com" in resp.headers["location"]


class TestOAuthCallbackEndpoint:
    """@brief GET /api/v1/oauth/{slug}/callback tests."""

    @pytest.mark.asyncio
    async def test_callback_returns_302_to_frontend(self, test_app):
        """Callback with valid state/code returns 302 redirect to frontend."""
        mock_provider = MagicMock()
        mock_provider.id = uuid.uuid4()
        mock_provider.slug = "oidc"
        mock_provider.provider_type = "oidc"
        mock_provider.authorization_endpoint = "https://auth.example.com/authorize"
        mock_provider.token_endpoint = "https://auth.example.com/token"

        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()

        with (
            patch("app.api.v1.oauth.ProviderManager") as mock_manager_cls,
            patch("app.api.v1.oauth.OAuthFlow") as mock_flow_cls,
            patch(
                "app.api.v1.oauth.verify_id_token",
                new_callable=AsyncMock,
                return_value={"sub": "user-123", "email": "u@ex.com"},
            ),
            patch("app.api.v1.oauth.UserProvisioner") as mock_provisioner_cls,
            patch("app.api.v1.oauth._get_valkey_client") as mock_valkey,
        ):
            mock_manager = AsyncMock()
            mock_manager.get_provider = AsyncMock(return_value=mock_provider)
            mock_manager_cls.return_value = mock_manager

            mock_flow = MagicMock()
            mock_flow.exchange_code = AsyncMock(
                return_value={"access_token": "at", "id_token": "id"}
            )
            mock_flow_cls.return_value = mock_flow

            mock_provisioner = AsyncMock()
            mock_provisioner.provision_user = AsyncMock(return_value=mock_user)
            mock_provisioner_cls.return_value = mock_provisioner

            mock_redis = AsyncMock()
            mock_redis.setex = AsyncMock()
            mock_redis.delete = AsyncMock()
            mock_valkey.return_value = mock_redis

            transport = ASGITransport(app=test_app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
                follow_redirects=False,
                cookies={
                    "oauth_state": "state-123",
                    "oauth_verifier": "verifier-456",
                    "oauth_provider": "oidc",
                    "oauth_nonce": "nonce-789",
                },
            ) as client:
                resp = await client.get(
                    "/api/v1/oauth/oidc/callback?code=auth-code&state=state-123"
                )

            assert resp.status_code == 302
            assert "location" in resp.headers


class TestOAuthExchangeEndpoint:
    """@brief POST /api/v1/oauth/exchange tests."""

    @pytest.mark.asyncio
    async def test_exchange_returns_access_token_and_cookie(self, test_app):
        """POST /oauth/exchange with valid code returns access_token and refresh cookie."""
        user_id = uuid.uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.role = "member"
        mock_user.community_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

        with (
            patch("app.api.v1.oauth._get_valkey_client") as mock_valkey,
            patch("app.api.v1.oauth.AuthService") as mock_auth_cls,
            patch("app.api.v1.oauth.UserRepository") as mock_repo_cls,
        ):
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(
                return_value='{"user_id": "' + str(user_id) + '", "provider_slug": "oidc"}'
            )
            mock_redis.delete = AsyncMock()
            mock_valkey.return_value = mock_redis

            mock_auth = MagicMock()
            mock_auth._issue_tokens = AsyncMock(
                return_value={
                    "access_token": "jwt-token",
                    "expires_in": 900,
                    "raw_refresh_token": "refresh-hex",
                }
            )
            mock_auth_cls.return_value = mock_auth

            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_repo_cls.return_value = mock_repo

            transport = ASGITransport(app=test_app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/v1/oauth/exchange",
                    json={"code": "exchange-code-123"},
                )

            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert data["access_token"] == "jwt-token"
            assert "set-cookie" in resp.headers or "refresh_token" in str(
                resp.headers.get("set-cookie", "")
            )

    @pytest.mark.asyncio
    async def test_exchange_invalid_code_returns_401(self, test_app):
        """POST /oauth/exchange with invalid code returns 401."""
        with patch("app.api.v1.oauth._get_valkey_client") as mock_valkey:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_valkey.return_value = mock_redis

            transport = ASGITransport(app=test_app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/v1/oauth/exchange",
                    json={"code": "invalid-code"},
                )

            assert resp.status_code == 401


class TestAuthConfigWithOAuthProviders:
    """@brief GET /api/v1/auth/config returns oauth_providers."""

    @pytest.mark.asyncio
    async def test_config_includes_oauth_providers_list(self, test_app):
        """Auth config returns oauth_providers array."""
        mock_provider = MagicMock()
        mock_provider.slug = "oidc"
        mock_provider.display_name = "OIDC"
        mock_provider.icon_url = "https://example.com/icon.png"

        with patch("app.services.oauth.provider_manager.ProviderManager") as mock_manager_cls:
            mock_manager = AsyncMock()
            mock_manager.get_enabled_providers = AsyncMock(return_value=[mock_provider])
            mock_manager_cls.return_value = mock_manager

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/auth/config")

            assert resp.status_code == 200
            data = resp.json()
            assert "oauth_providers" in data
            assert len(data["oauth_providers"]) == 1
            assert data["oauth_providers"][0]["slug"] == "oidc"
            assert data["oauth_providers"][0]["display_name"] == "OIDC"
