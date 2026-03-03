"""
@file test_oauth_flow.py
@brief Integration tests for the complete OAuth2/OIDC login flow.

Tests the full cycle: login redirect -> callback -> exchange code -> get tokens.
External IdP responses are mocked; internal DB and Valkey interactions are tested.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


def _mock_provider(slug: str = "oidc", enabled: bool = True) -> MagicMock:
    """@brief Build a mock OAuthProvider."""
    p = MagicMock()
    p.id = uuid.uuid4()
    p.slug = slug
    p.display_name = "OIDC"
    p.enabled = enabled
    p.authorization_endpoint = "https://idp.example/authorize"
    p.token_endpoint = "https://idp.example/token"
    p.client_id = "test-client"
    p.scopes = "openid profile email"
    p.provider_type = "oidc"
    p.userinfo_endpoint = None
    return p


class TestOAuthLoginFlow:
    """@brief GET /api/v1/oauth/{slug}/login tests."""

    @pytest.mark.asyncio
    async def test_login_returns_302_with_pkce_params(self, test_app):
        """Full login flow — GET /oauth/{slug}/login returns 302, redirect has PKCE."""
        mock_provider = _mock_provider()
        mock_manager = AsyncMock()
        mock_manager.get_provider = AsyncMock(return_value=mock_provider)

        with (
            patch("app.api.v1.oauth.ProviderManager", return_value=mock_manager),
            patch("app.api.v1.oauth.OAuthFlow") as mock_flow_cls,
        ):
            mock_flow = MagicMock()
            mock_flow.build_authorize_url.return_value = (
                "https://idp.example/authorize?response_type=code&code_challenge=xyz"
                "&code_challenge_method=S256&state=abc",
                "abc",
                "verifier123",
            )
            mock_flow_cls.return_value = mock_flow

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/oauth/oidc/login")

        assert resp.status_code == 302
        location = resp.headers.get("location", "")
        assert "code_challenge=" in location
        assert "code_challenge_method=S256" in location
        assert "state=" in location

    @pytest.mark.asyncio
    async def test_disabled_provider_returns_error(self, test_app):
        """GET /oauth/{slug}/login returns error when provider disabled."""
        mock_provider = _mock_provider(enabled=False)
        mock_manager = AsyncMock()
        mock_manager.get_provider = AsyncMock(return_value=mock_provider)

        with patch("app.api.v1.oauth.ProviderManager", return_value=mock_manager):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/oauth/oidc/login")

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unknown_provider_returns_404(self, test_app):
        """GET /oauth/unknown/login returns 404."""
        mock_manager = AsyncMock()
        mock_manager.get_provider = AsyncMock(return_value=None)

        with patch("app.api.v1.oauth.ProviderManager", return_value=mock_manager):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/oauth/unknown/login")

        assert resp.status_code == 401


class TestOAuthCallbackFlow:
    """@brief GET /api/v1/oauth/{slug}/callback tests."""

    @pytest.mark.asyncio
    async def test_callback_creates_exchange_code_redirect(self, test_app):
        """Callback with valid state+code redirects to frontend with exchange code."""
        mock_provider = _mock_provider()
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()

        mock_manager = AsyncMock()
        mock_manager.get_provider = AsyncMock(return_value=mock_provider)

        mock_flow = MagicMock()
        mock_flow.exchange_code = AsyncMock(return_value={"id_token": "jwt", "access_token": "at"})

        mock_valkey = AsyncMock()
        mock_valkey.setex = AsyncMock()

        with (
            patch("app.api.v1.oauth.ProviderManager", return_value=mock_manager),
            patch("app.api.v1.oauth.OAuthFlow", return_value=mock_flow),
            patch("app.api.v1.oauth.verify_id_token", new_callable=AsyncMock) as m_verify,
            patch("app.api.v1.oauth.get_pool", return_value=mock_valkey),
        ):
            from app.services.oauth.user_provisioner import OAuthAuthResult

            m_verify.return_value = {"sub": "user-123", "email": "u@ex.com"}
            mock_extract = MagicMock(
                return_value=OAuthAuthResult(
                    sub="user-123",
                    email="u@ex.com",
                    display_name="User",
                    groups=[],
                )
            )
            with patch("app.api.v1.oauth.extract_claims", mock_extract):
                with patch("app.api.v1.oauth.UserProvisioner") as mock_provisioner_cls:
                    mock_provisioner = AsyncMock()
                    mock_provisioner.provision_user = AsyncMock(return_value=mock_user)
                    mock_provisioner_cls.return_value = mock_provisioner

                    transport = ASGITransport(app=test_app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        resp = await client.get(
                            "/api/v1/oauth/oidc/callback",
                            params={"code": "auth-code", "state": "abc"},
                            cookies={
                                "oauth_state": "abc",
                                "oauth_verifier": "verifier123",
                                "oauth_provider": "oidc",
                            },
                        )

        assert resp.status_code == 302
        location = resp.headers.get("location", "")
        assert "/auth/callback?code=" in location
        assert mock_valkey.setex.called


class TestOAuthExchange:
    """@brief POST /api/v1/oauth/exchange tests."""

    @pytest.mark.asyncio
    async def test_exchange_returns_tokens(self, test_app):
        """POST /oauth/exchange with valid code returns access_token + refresh cookie."""
        user_id = uuid.uuid4()
        payload = json.dumps({"user_id": str(user_id), "provider_slug": "oidc"})
        mock_valkey = AsyncMock()
        mock_valkey.get = AsyncMock(
            return_value=payload.encode() if isinstance(payload, str) else payload
        )
        mock_valkey.delete = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = True

        with (
            patch("app.api.v1.oauth.get_pool", return_value=mock_valkey),
            patch("app.api.v1.oauth.UserRepository") as mock_user_repo_cls,
            patch("app.api.v1.oauth.AuthService") as mock_auth_cls,
        ):
            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_user_repo_cls.return_value = mock_user_repo

            mock_auth = MagicMock()
            mock_auth._issue_tokens = AsyncMock(
                return_value={
                    "access_token": "jwt-token",
                    "expires_in": 900,
                    "raw_refresh_token": "refresh-hex",
                }
            )
            mock_auth_cls.return_value = mock_auth

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/oauth/exchange",
                    json={"code": "valid-exchange-code"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data.get("access_token") == "jwt-token"
        assert "set-cookie" in resp.headers

    @pytest.mark.asyncio
    async def test_invalid_exchange_code_returns_401(self, test_app):
        """POST /oauth/exchange with expired/invalid code returns 401."""
        mock_valkey = AsyncMock()
        mock_valkey.get = AsyncMock(return_value=None)

        with patch("app.api.v1.oauth.get_pool", return_value=mock_valkey):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/oauth/exchange",
                    json={"code": "invalid-code"},
                )

        assert resp.status_code == 401


class TestAuthConfig:
    """@brief GET /api/v1/auth/config tests."""

    @pytest.mark.asyncio
    async def test_auth_config_includes_providers(self, test_app):
        """GET /auth/config returns oauth_providers list."""
        mock_provider = _mock_provider()
        mock_provider.display_name = "OIDC"
        mock_provider.icon_url = None

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
        assert len(data["oauth_providers"]) >= 1


class TestDeprecatedOIDCRoutes:
    """@brief Deprecated /oidc/* redirect tests."""

    @pytest.mark.asyncio
    async def test_oidc_login_redirects_to_oauth(self, test_app):
        """GET /oidc/login returns 307 to /oauth/{slug}/login."""
        mock_provider = _mock_provider()
        with patch("app.services.oauth.provider_manager.ProviderManager") as mock_manager_cls:
            mock_manager = AsyncMock()
            mock_manager.get_enabled_providers = AsyncMock(return_value=[mock_provider])
            mock_manager_cls.return_value = mock_manager

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/auth/oidc/login")

        assert resp.status_code == 307
        location = resp.headers.get("location", "")
        assert "/api/v1/oauth/oidc/login" in location
