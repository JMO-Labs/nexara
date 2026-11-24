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
            # L1: the page is app/(auth)/callback -> URL /callback (route groups vanish).
            location = resp.headers["location"]
            base, _, code = location.partition("/callback?code=")
            assert base.startswith("http") and base.count("/") == 2  # public base, no path
            assert mock_redis.setex.await_args.args[0] == f"oauth_exchange:{code}"

    @pytest.mark.asyncio
    async def test_callback_refusal_redirects_to_login_with_code(self, test_app):
        """SSO refusal: no exchange code, redirect to /login?error=<code>."""
        from app.core.exceptions import SsoRefusedError

        provider = MagicMock(id=uuid.uuid4(), provider_type="oidc", preset=None)
        provider.display_name = "Acme SSO&x"
        uid = uuid.uuid4()
        log_failure = AsyncMock()
        with (
            patch("app.api.v1.oauth.log_failure", log_failure),
            patch("app.api.v1.oauth.ProviderManager") as manager_cls,
            patch("app.api.v1.oauth.OAuthFlow") as flow_cls,
            patch(
                "app.api.v1.oauth.verify_id_token",
                new_callable=AsyncMock,
                return_value={"sub": "u1", "email": "a@other.com"},
            ),
            patch("app.api.v1.oauth.UserProvisioner") as prov_cls,
            patch("app.api.v1.oauth._get_valkey_client") as valkey,
        ):
            manager_cls.return_value.get_provider = AsyncMock(return_value=provider)
            flow_cls.return_value.exchange_code = AsyncMock(
                return_value={"access_token": "at", "id_token": "id"}
            )
            prov_cls.return_value.provision_user = AsyncMock(
                side_effect=SsoRefusedError("sso_domain_not_allowed", user_id=uid)
            )
            async with AsyncClient(
                transport=ASGITransport(app=test_app),
                base_url="http://test",
                follow_redirects=False,
                cookies={
                    "oauth_state": "st",
                    "oauth_verifier": "v",
                    "oauth_provider": "oidc",
                    "oauth_nonce": "n",
                },
            ) as client:
                resp = await client.get("/api/v1/oauth/oidc/callback?code=c&state=st")
        assert resp.status_code == 302
        assert resp.headers["location"].endswith(
            "/login?error=sso_domain_not_allowed&provider=Acme+SSO%26x"
        )
        valkey.return_value.setex.assert_not_called()
        args, kwargs = log_failure.await_args
        assert args[2:5] == ("a@other.com", "sso", "sso_domain_not_allowed")
        assert kwargs["user_id"] == uid


class TestOAuthExchangeEndpoint:
    """@brief POST /api/v1/oauth/exchange tests."""

    @pytest.mark.asyncio
    async def test_exchange_returns_access_token_and_cookie(self, test_app):
        """POST /oauth/exchange with valid code returns access_token and refresh cookie."""
        user_id = uuid.uuid4()

        with (
            patch("app.api.v1.oauth._get_valkey_client") as mock_valkey,
            patch("app.api.v1.oauth.AuthService") as mock_auth_cls,
        ):
            mock_redis = AsyncMock()
            mock_redis.getdel = AsyncMock(
                return_value='{"user_id": "' + str(user_id) + '", "provider_slug": "oidc"}'
            )
            mock_valkey.return_value = mock_redis

            mock_auth = MagicMock()
            mock_auth.exchange_sso = AsyncMock(
                return_value={
                    "access_token": "jwt-token",
                    "expires_in": 900,
                    "raw_refresh_token": "refresh-hex",
                }
            )
            mock_auth_cls.return_value = mock_auth

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
            mock_redis.getdel = AsyncMock(return_value=None)
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
        mock_provider.preset = "google"

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
            assert data["oauth_providers"][0]["preset"] == "google"
            assert data["oauth_providers"][0]["slug"] == "oidc"
            assert data["oauth_providers"][0]["display_name"] == "OIDC"
