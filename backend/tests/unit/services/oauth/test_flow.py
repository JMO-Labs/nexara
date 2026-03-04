"""
@file test_flow.py
@brief Unit tests for OAuth2 authorization code flow with PKCE.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthenticationError
from app.services.oauth.flow import OAuthFlow


def _make_provider(
    authorization_endpoint="https://idp.example.com/authorize",
    token_endpoint="https://idp.example.com/token",
    client_id="test-client",
    scopes="openid profile email",
    client_secret_encrypted="encrypted-secret",
):
    """Create a mock OAuth provider with required attributes."""
    provider = MagicMock()
    provider.authorization_endpoint = authorization_endpoint
    provider.token_endpoint = token_endpoint
    provider.client_id = client_id
    provider.scopes = scopes
    provider.client_secret_encrypted = client_secret_encrypted
    provider.id = uuid.uuid4()
    return provider


class TestBuildAuthorizeUrl:
    """@brief Tests for OAuthFlow.build_authorize_url."""

    def test_includes_code_challenge_and_s256_method(self):
        """build_authorize_url includes code_challenge and S256 method."""
        flow = OAuthFlow()
        provider = _make_provider()
        url, state, verifier = flow.build_authorize_url(provider, "https://app.example.com/callback")
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url

    def test_returns_state_and_verifier_strings(self):
        """build_authorize_url returns state and verifier strings."""
        flow = OAuthFlow()
        provider = _make_provider()
        url, state, verifier = flow.build_authorize_url(provider, "https://app.example.com/callback")
        assert isinstance(state, str) and len(state) > 0
        assert isinstance(verifier, str) and len(verifier) > 0

    def test_uses_provider_authorization_endpoint(self):
        """build_authorize_url uses provider's authorization_endpoint."""
        flow = OAuthFlow()
        provider = _make_provider(authorization_endpoint="https://custom-idp.com/auth")
        url, _, _ = flow.build_authorize_url(provider, "https://app.example.com/callback")
        assert url.startswith("https://custom-idp.com/auth?")


class TestExchangeCode:
    """@brief Tests for OAuthFlow.exchange_code."""

    @pytest.mark.asyncio
    async def test_calls_token_endpoint_with_correct_params(self):
        """exchange_code calls token_endpoint with correct params (mock httpx)."""
        flow = OAuthFlow()
        provider = _make_provider(token_endpoint="https://idp.example.com/token")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"access_token": "at", "id_token": "it"}
        mock_resp.text = "{}"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.oauth.flow.decrypt_secret", return_value="decrypted-secret"):
            with patch("app.services.oauth.flow.derive_fernet_key", return_value=b"key"):
                with patch("app.services.oauth.flow.httpx.AsyncClient", return_value=mock_client):
                    result = await flow.exchange_code(
                        provider, "auth-code", "verifier", "https://app/cb", "secret-key"
                    )

        assert result["access_token"] == "at"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://idp.example.com/token"
        assert call_args[1]["data"]["grant_type"] == "authorization_code"
        assert call_args[1]["data"]["code"] == "auth-code"
        assert call_args[1]["data"]["code_verifier"] == "verifier"
        assert call_args[1]["data"]["client_secret"] == "decrypted-secret"

    @pytest.mark.asyncio
    async def test_raises_authentication_error_on_non_200(self):
        """exchange_code raises AuthenticationError on non-200 response."""
        flow = OAuthFlow()
        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.oauth.flow.decrypt_secret", return_value="decrypted"):
            with patch("app.services.oauth.flow.derive_fernet_key", return_value=b"key"):
                with patch("app.services.oauth.flow.httpx.AsyncClient", return_value=mock_client):
                    with pytest.raises(AuthenticationError, match="token exchange failed"):
                        await flow.exchange_code(
                            provider, "code", "verifier", "https://app/cb", "secret"
                        )

    @pytest.mark.asyncio
    async def test_raises_authentication_error_when_no_token_endpoint(self):
        """exchange_code raises AuthenticationError when no token_endpoint."""
        flow = OAuthFlow()
        provider = _make_provider(token_endpoint=None)

        with patch("app.services.oauth.flow.decrypt_secret", return_value="decrypted"):
            with patch("app.services.oauth.flow.derive_fernet_key", return_value=b"key"):
                with pytest.raises(AuthenticationError, match="no token endpoint"):
                    await flow.exchange_code(
                        provider, "code", "verifier", "https://app/cb", "secret"
                    )
