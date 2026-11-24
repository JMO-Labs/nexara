"""
@file test_insecure_discovery.py
@brief OAUTH_ALLOW_INSECURE_DISCOVERY: off rejects http/private hosts; on allows and warns.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from structlog.testing import capture_logs

from app.core.config import Settings
from app.services.oauth import discovery

URL = "http://authentik:9100/application/o/nexara/.well-known/openid-configuration"
DOC = {
    "issuer": "http://authentik:9100/application/o/nexara/",
    "authorization_endpoint": "http://authentik:9100/authorize",
    "token_endpoint": "http://authentik:9100/token",
}


def _settings(allow: bool) -> Settings:
    return Settings(SECRET_KEY="k", OAUTH_ALLOW_INSECURE_DISCOVERY=allow)


def _client():
    resp = MagicMock(json=MagicMock(return_value=DOC), raise_for_status=MagicMock())
    client = AsyncMock()
    client.get.return_value = resp
    cm = AsyncMock()
    cm.__aenter__.return_value = client
    return cm


@pytest.fixture(autouse=True)
def _clear():
    discovery.clear_cache()
    yield
    discovery.clear_cache()


def test_default_is_off():
    assert Settings(SECRET_KEY="k").OAUTH_ALLOW_INSECURE_DISCOVERY is False


@pytest.mark.parametrize("url", [URL, "https://10.0.0.5/.well-known/openid-configuration"])
async def test_off_rejects_http_and_private(url):
    with patch("app.core.config.get_settings", return_value=_settings(False)):
        with pytest.raises(ValueError):
            await discovery.fetch_discovery(url)
        with pytest.raises(ValueError):
            await discovery.discover_endpoints(url.rsplit("/.well-known", 1)[0])


async def test_on_allows_http_private_and_warns():
    with (
        patch("app.core.config.get_settings", return_value=_settings(True)),
        patch.object(discovery.httpx, "AsyncClient", return_value=_client()),
        capture_logs() as logs,
    ):
        doc = await discovery.fetch_discovery(URL)
    assert doc["issuer"] == DOC["issuer"]
    assert any(
        e["event"] == "oauth_insecure_discovery_allowed" and e["log_level"] == "warning"
        for e in logs
    )
