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
