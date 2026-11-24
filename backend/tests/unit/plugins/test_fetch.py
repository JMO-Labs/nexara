"""
@file
@brief Manifest fetch: https-only and SSRF guard unless the dev flag is set.
"""

import pytest

from app.core.exceptions import AppError
from app.plugins.fetch import fetch_manifest_text


@pytest.mark.parametrize("url", ["http://example.com/m.toml", "file:///etc/passwd", "https:///x"])
async def test_rejects_non_https(url):
    with pytest.raises(AppError) as e:
        await fetch_manifest_text(url)
    assert e.value.code == "manifest_url_invalid"


async def test_rejects_private_host():
    with pytest.raises(AppError) as e:
        await fetch_manifest_text("https://127.0.0.1/m.toml")
    assert e.value.code == "manifest_url_invalid"


async def test_non_2xx_is_fetch_failed():
    from unittest.mock import AsyncMock, patch

    import httpx

    err = httpx.HTTPStatusError(
        "404", request=httpx.Request("GET", "https://x"), response=httpx.Response(404)
    )
    with patch("app.plugins.fetch.safe_fetch", AsyncMock(side_effect=err)):
        with pytest.raises(AppError) as e:
            await fetch_manifest_text("https://example.com/m.toml")
    assert e.value.code == "manifest_fetch_failed"


async def test_total_deadline(monkeypatch):
    import asyncio
    from unittest.mock import patch

    async def slow(*a, **k):
        await asyncio.sleep(5)

    monkeypatch.setattr("app.plugins.fetch.TIMEOUT", 0.05)
    with patch("app.plugins.fetch.safe_fetch", slow):
        with pytest.raises(AppError) as e:
            await fetch_manifest_text("https://example.com/m.toml")
    assert e.value.code == "manifest_fetch_failed"
