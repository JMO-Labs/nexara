"""
@file test_discovery.py
@brief Tests for OIDC discovery service.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.oauth.discovery import _is_disallowed_host, discover_endpoints


class TestIsDisallowedHost:
    """@brief Tests for _is_disallowed_host function."""

    def test_rejects_localhost(self):
        """_is_disallowed_host rejects localhost."""
        assert _is_disallowed_host("localhost") is True

    def test_rejects_127_0_0_1(self):
        """_is_disallowed_host rejects 127.0.0.1."""
        assert _is_disallowed_host("127.0.0.1") is True

    def test_rejects_private_ip(self):
        """_is_disallowed_host rejects private IP 10.0.0.1."""
        assert _is_disallowed_host("10.0.0.1") is True

    def test_allows_public_hostname(self):
        """_is_disallowed_host allows public hostname idp.example.com."""
        assert _is_disallowed_host("idp.example.com") is False


class TestDiscoverEndpointsHappyPath:
    """@brief Happy path: valid openid-configuration response."""

    @pytest.mark.asyncio
    async def test_returns_all_endpoints(self):
        """@brief Valid JSON returns authorization, token, userinfo, jwks_uri, end_session."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "authorization_endpoint": "https://idp.example.com/authorize",
            "token_endpoint": "https://idp.example.com/token",
            "userinfo_endpoint": "https://idp.example.com/userinfo",
            "jwks_uri": "https://idp.example.com/.well-known/jwks.json",
            "end_session_endpoint": "https://idp.example.com/logout",
        }
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.oauth.discovery.httpx.AsyncClient",
            return_value=mock_client,
        ):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            result = await discover_endpoints("https://idp.example.com")

        assert result["authorization_endpoint"] == "https://idp.example.com/authorize"
        assert result["token_endpoint"] == "https://idp.example.com/token"
        assert result["userinfo_endpoint"] == "https://idp.example.com/userinfo"
        assert result["jwks_uri"] == "https://idp.example.com/.well-known/jwks.json"
        assert result["end_session_endpoint"] == "https://idp.example.com/logout"


class TestDiscoverEndpointsSSRF:
    """@brief SSRF protection: reject private/local URLs."""

    @pytest.mark.asyncio
    async def test_rejects_http_scheme(self):
        """@brief Reject http:// (non-HTTPS)."""
        with pytest.raises(ValueError, match="https"):
            await discover_endpoints("http://example.com")

    @pytest.mark.asyncio
    async def test_rejects_localhost(self):
        """@brief Reject https://localhost."""
        with pytest.raises(ValueError, match="localhost|private|disallowed"):
            await discover_endpoints("https://localhost")

    @pytest.mark.asyncio
    async def test_rejects_127_0_0_1(self):
        """@brief Reject https://127.0.0.1."""
        with pytest.raises(ValueError, match="127|private|disallowed"):
            await discover_endpoints("https://127.0.0.1")

    @pytest.mark.asyncio
    async def test_rejects_10_0_0_1(self):
        """@brief Reject https://10.0.0.1 (private range)."""
        with pytest.raises(ValueError, match="private|disallowed"):
            await discover_endpoints("https://10.0.0.1")

    @pytest.mark.asyncio
    async def test_rejects_192_168_1_1(self):
        """@brief Reject https://192.168.1.1 (private range)."""
        with pytest.raises(ValueError, match="private|disallowed"):
            await discover_endpoints("https://192.168.1.1")

    @pytest.mark.asyncio
    async def test_rejects_172_16_0_1(self):
        """@brief Reject https://172.16.0.1 (private range)."""
        with pytest.raises(ValueError, match="private|disallowed"):
            await discover_endpoints("https://172.16.0.1")


class TestDiscoverEndpointsMalformed:
    """@brief Malformed response handling."""

    @pytest.mark.asyncio
    async def test_missing_required_fields_raises(self):
        """@brief Missing required fields raises ValueError."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token_endpoint": "https://idp.example.com/token"}
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.oauth.discovery.httpx.AsyncClient",
            return_value=mock_client,
        ):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            with pytest.raises(ValueError, match="required|missing"):
                await discover_endpoints("https://idp.example.com")


class TestDiscoverEndpointsNetworkError:
    """@brief Network error handling."""

    @pytest.mark.asyncio
    async def test_request_error_raises_descriptive(self):
        """@brief httpx.RequestError raises a descriptive error."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.RequestError("Connection refused"))

        with patch(
            "app.services.oauth.discovery.httpx.AsyncClient",
            return_value=mock_client,
        ):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            with pytest.raises(
                (httpx.RequestError, ValueError, Exception),
                match="Connection|discovery|failed",
            ):
                await discover_endpoints("https://idp.example.com")


class TestDiscoverEndpointsNon200:
    """@brief Non-200 status code handling."""

    @pytest.mark.asyncio
    async def test_non_200_raises_error(self):
        """@brief Non-200 status code raises error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_response
        )
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.oauth.discovery.httpx.AsyncClient",
            return_value=mock_client,
        ):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            with pytest.raises((httpx.HTTPStatusError, ValueError, Exception)):
                await discover_endpoints("https://idp.example.com")
