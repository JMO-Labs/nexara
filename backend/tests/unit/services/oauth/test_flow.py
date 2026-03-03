"""
@file test_flow.py
@brief Tests for OAuthFlow: authorize URL, code exchange.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthenticationError
from app.models.oauth_provider import OAuthProvider
from app.services.oauth.flow import OAuthFlow


def _make_provider(
    authorization_endpoint: str = "https://idp.example.com/authorize",
    token_endpoint: str = "https://idp.example.com/token",
    scopes: str = "openid profile email",
) -> OAuthProvider:
    """@brief Create a mock OAuthProvider."""
    p = MagicMock(spec=OAuthProvider)
    p.authorization_endpoint = authorization_endpoint
    p.token_endpoint = token_endpoint
    p.client_id = "test-client"
    p.scopes = scopes
    return p


class TestBuildAuthorizeUrl:
    """@brief build_authorize_url returns URL with PKCE."""

    def test_returns_url_state_code_verifier(self):
        """@brief Returns (url, state, code_verifier) with PKCE params."""
        provider = _make_provider()
        flow = OAuthFlow()

        url, state, code_verifier = flow.build_authorize_url(
            provider, "https://app.example.com/callback"
        )

        assert "https://idp.example.com/authorize" in url
        assert "client_id=test-client" in url
        assert "redirect_uri=" in url
        assert "state=" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        assert "response_type=code" in url
        assert state
        assert code_verifier
        assert len(code_verifier) > 20


class TestExchangeCode:
    """@brief exchange_code exchanges auth code for tokens."""

    @pytest.mark.asyncio
    async def test_returns_token_dict_on_success(self):
        """@brief Mock httpx returns 200 -> token dict."""
        provider = _make_provider()
        provider.client_secret_encrypted = "encrypted"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "at",
            "id_token": "id",
            "expires_in": 3600,
        }
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with (
            patch("app.services.oauth.flow.decrypt_secret", return_value="plain-secret"),
            patch(
                "app.services.oauth.flow.httpx.AsyncClient",
                return_value=mock_client,
            ),
        ):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            flow = OAuthFlow()
            result = await flow.exchange_code(
                provider,
                "auth-code",
                "code-verifier",
                "https://app.example.com/callback",
                "secret-key",
            )

        assert result["access_token"] == "at"
        assert result["id_token"] == "id"

    @pytest.mark.asyncio
    async def test_non_200_raises_authentication_error(self):
        """@brief Non-200 response raises AuthenticationError."""
        provider = _make_provider()
        provider.client_secret_encrypted = "encrypted"
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "invalid_grant"

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with (
            patch("app.services.oauth.flow.decrypt_secret", return_value="plain-secret"),
            patch(
                "app.services.oauth.flow.httpx.AsyncClient",
                return_value=mock_client,
            ),
        ):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            flow = OAuthFlow()
            with pytest.raises(AuthenticationError, match="exchange|failed|invalid"):
                await flow.exchange_code(
                    provider,
                    "bad-code",
                    "verifier",
                    "https://app.example.com/callback",
                    "secret-key",
                )
