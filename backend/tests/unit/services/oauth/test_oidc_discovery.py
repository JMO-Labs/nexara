"""
@file test_oidc_discovery.py
@brief Tests for discovery_url fetching, 24h caching and HTTPS enforcement.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.oauth import discovery

URL = "https://kc.example.com/realms/x/.well-known/openid-configuration"
DOC = {
    "issuer": "https://kc.example.com/realms/x",
    "authorization_endpoint": "https://kc.example.com/auth",
    "token_endpoint": "https://kc.example.com/token",
    "jwks_uri": "https://kc.example.com/jwks",
}


def _client(doc):
    resp = MagicMock()
    resp.json.return_value = doc
    resp.raise_for_status = MagicMock()
    c = AsyncMock()
    c.get = AsyncMock(return_value=resp)
    c.__aenter__ = AsyncMock(return_value=c)
    c.__aexit__ = AsyncMock(return_value=False)
    return c


@pytest.fixture(autouse=True)
def _clear():
    discovery.clear_cache()


@pytest.mark.asyncio
async def test_fetch_returns_document_with_issuer():
    c = _client(DOC)
    with patch("app.services.oauth.discovery.httpx.AsyncClient", return_value=c):
        result = await discovery.fetch_discovery(URL)
    assert result["issuer"] == DOC["issuer"]
    assert result["jwks_uri"] == DOC["jwks_uri"]


@pytest.mark.asyncio
async def test_second_call_served_from_cache():
    c = _client(DOC)
    with patch("app.services.oauth.discovery.httpx.AsyncClient", return_value=c):
        await discovery.fetch_discovery(URL)
        await discovery.fetch_discovery(URL)
    c.get.assert_called_once()


@pytest.mark.asyncio
async def test_cache_expires_after_24h():
    c = _client(DOC)
    with patch("app.services.oauth.discovery.httpx.AsyncClient", return_value=c):
        with patch("app.services.oauth.discovery.time.monotonic", return_value=1000.0):
            await discovery.fetch_discovery(URL)
        with patch("app.services.oauth.discovery.time.monotonic", return_value=1000.0 + 86401):
            await discovery.fetch_discovery(URL)
    assert c.get.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad",
    [
        "http://kc.example.com/.well-known/openid-configuration",
        "https://localhost/.well-known/openid-configuration",
        "https://10.0.0.5/.well-known/openid-configuration",
    ],
)
async def test_rejects_http_and_private(bad):
    with pytest.raises(ValueError):
        await discovery.fetch_discovery(bad)


@pytest.mark.asyncio
async def test_rejects_issuer_not_https():
    doc = {**DOC, "issuer": "http://kc.example.com"}
    with patch("app.services.oauth.discovery.httpx.AsyncClient", return_value=_client(doc)):
        with pytest.raises(ValueError):
            await discovery.fetch_discovery(URL)
