"""
@file fetch.py
@brief SSRF-guarded fetch of a plugin manifest from an admin-supplied URL.
"""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.http_safe import UnsafeUrlError, safe_fetch
from app.plugins.manifest import MAX_MANIFEST_BYTES

TIMEOUT = 10.0


def _fail(code: str, message: str) -> AppError:
    return AppError(code=code, message=message, status_code=422)


async def _fetch_dev(url: str) -> bytes:
    """@brief Dev-only fetch (private hosts allowed); streams with the size cap."""
    buf = bytearray()
    async with (
        httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as c,
        c.stream("GET", url) as resp,
    ):
        resp.raise_for_status()
        async for chunk in resp.aiter_bytes():
            buf += chunk
            if len(buf) > MAX_MANIFEST_BYTES:
                break
    return bytes(buf[: MAX_MANIFEST_BYTES + 1])


async def fetch_manifest_text(url: str) -> str:
    """
    @brief Download manifest TOML (10 s total deadline, 64 KiB cap, https hops only, 2xx only).

    https only and public hosts only, unless ``PLUGINS_ALLOW_INSECURE_URLS``.
    @raises AppError ``manifest_url_invalid`` / ``manifest_fetch_failed`` (422).
    """
    insecure = get_settings().PLUGINS_ALLOW_INSECURE_URLS
    parsed = urlparse(url)
    allowed = ("http", "https") if insecure else ("https",)
    if parsed.scheme not in allowed or not parsed.hostname:
        raise _fail("manifest_url_invalid", "Manifest URL must be https")
    try:
        async with asyncio.timeout(TIMEOUT):
            if insecure:
                data = await _fetch_dev(url)
            else:
                data = await safe_fetch(
                    url, timeout=TIMEOUT, max_bytes=MAX_MANIFEST_BYTES + 1, strict=True
                )
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


def trusted_host(url: str) -> bool:
    """@brief ``url`` has exactly the configured ``PLUGIN_HOST_URL`` origin (scheme + netloc)."""
    host = get_settings().PLUGIN_HOST_URL
    if not host:
        return False
    a, b = urlparse(url), urlparse(host)
    return (a.scheme, a.netloc) == (b.scheme, b.netloc)


def endpoint_allowed(url: str) -> bool:
    """@brief Delivery would accept this endpoint: https, or the dev flag / plugin host."""
    if urlparse(url).scheme == "https":
        return True
    return bool(get_settings().PLUGINS_ALLOW_INSECURE_URLS) or trusted_host(url)
