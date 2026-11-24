"""
@file fetch.py
@brief SSRF-guarded fetch of a plugin manifest from an admin-supplied URL.
"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.http_safe import UnsafeUrlError, safe_fetch
from app.plugins.manifest import MAX_MANIFEST_BYTES

TIMEOUT = 10.0


def _fail(code: str, message: str) -> AppError:
    return AppError(code=code, message=message, status_code=422)


async def fetch_manifest_text(url: str) -> str:
    """
    @brief Download manifest TOML (10 s total, 64 KiB cap, no redirects to private hosts).

    https only and public hosts only, unless ``PLUGINS_ALLOW_INSECURE_URLS``.
    @raises AppError ``manifest_url_invalid`` / ``manifest_fetch_failed`` (422).
    """
    insecure = get_settings().PLUGINS_ALLOW_INSECURE_URLS
    parsed = urlparse(url)
    allowed = ("http", "https") if insecure else ("https",)
    if parsed.scheme not in allowed or not parsed.hostname:
        raise _fail("manifest_url_invalid", "Manifest URL must be https")
    try:
        if insecure:
            async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as c:
                resp = await c.get(url)
                resp.raise_for_status()
                data = resp.content[: MAX_MANIFEST_BYTES + 1]
        else:
            data = await safe_fetch(url, timeout=TIMEOUT, max_bytes=MAX_MANIFEST_BYTES + 1)
    except UnsafeUrlError:
        raise _fail("manifest_url_invalid", "Manifest URL is not allowed") from None
    except (httpx.HTTPError, TimeoutError):
        raise _fail("manifest_fetch_failed", "Could not download the manifest") from None
    if len(data) > MAX_MANIFEST_BYTES:
        raise _fail("manifest_fetch_failed", "Manifest too large")
    try:
        return data.decode()
    except UnicodeDecodeError:
        raise _fail("manifest_fetch_failed", "Manifest is not valid UTF-8") from None
