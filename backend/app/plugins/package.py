"""
@file package.py
@brief Download a plugin package tarball, verify its sha256 and read its manifest.

The tarball is never extracted: only ``nexara-plugin.toml`` at the archive root is
read in memory, with caps on download size, member count and bytes walked.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import io
import re
import tarfile
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.http_safe import UnsafeUrlError, safe_fetch
from app.plugins.manifest import MAX_MANIFEST_BYTES, PluginManifest, parse_manifest

MAX_PACKAGE_BYTES = 50 * 1024 * 1024
MAX_MEMBERS = 10_000
MAX_WALK_BYTES = 512 * 1024 * 1024  # uncompressed bytes scanned before giving up
MANIFEST_NAME = "nexara-plugin.toml"
TIMEOUT = 60.0
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}", re.ASCII)


def _fail(code: str, message: str) -> AppError:
    return AppError(code=code, message=message, status_code=422)


async def _fetch_dev(url: str) -> bytes:
    """@brief Dev-only fetch (http/private hosts allowed), streamed with the size cap."""
    buf = bytearray()
    async with (
        httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False, trust_env=False) as c,
        c.stream("GET", url) as resp,
    ):
        resp.raise_for_status()
        async for chunk in resp.aiter_bytes():
            buf += chunk
            if len(buf) > MAX_PACKAGE_BYTES:
                break
    return bytes(buf[: MAX_PACKAGE_BYTES + 1])


async def download_package(url: str) -> bytes:
    """
    @brief Download a package (https and public hosts only unless the dev flag), ≤50 MB.
    @raises AppError ``package_url_invalid`` / ``package_fetch_failed`` / ``package_too_large``.
    """
    insecure = get_settings().PLUGINS_ALLOW_INSECURE_URLS
    parsed = urlparse(url)
    if parsed.scheme not in (("http", "https") if insecure else ("https",)) or not parsed.hostname:
        raise _fail("package_url_invalid", "Package URL must be https")
    try:
        async with asyncio.timeout(TIMEOUT):
            if insecure:
                data = await _fetch_dev(url)
            else:
                data = await safe_fetch(
                    url, timeout=TIMEOUT, max_bytes=MAX_PACKAGE_BYTES + 1, strict=True
                )
    except UnsafeUrlError:
        raise _fail("package_url_invalid", "Package URL is not allowed") from None
    except (httpx.HTTPError, TimeoutError):
        raise _fail("package_fetch_failed", "Could not download the package") from None
    if len(data) > MAX_PACKAGE_BYTES:
        raise _fail("package_too_large", "Package is larger than 50 MB")
    return data


def read_manifest_from_tar(data: bytes) -> str:
    """
    @brief Return the text of ``nexara-plugin.toml`` at the archive root, without extracting.
    @raises AppError ``invalid_manifest`` if missing, not a regular file, too large or the
        archive is unreadable.
    """
    walked = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
            for n, member in enumerate(tf):
                walked = member.offset_data + member.size
                if n >= MAX_MEMBERS or walked > MAX_WALK_BYTES:
                    break
                if member.name.removeprefix("./") != MANIFEST_NAME:
                    continue
                if not member.isreg() or member.size > MAX_MANIFEST_BYTES:
                    raise _invalid("nexara-plugin.toml must be a regular file under 64 KiB")
                fh = tf.extractfile(member)
                if fh is None:
                    raise _invalid("nexara-plugin.toml is unreadable")
                return fh.read(MAX_MANIFEST_BYTES + 1).decode()
    except (tarfile.TarError, EOFError, OSError, UnicodeDecodeError):
        raise _invalid("package is not a readable tar archive") from None
    raise _invalid("nexara-plugin.toml not found at the package root")


def _invalid(msg: str) -> AppError:
    return AppError(
        code="invalid_manifest",
        message="Invalid plugin manifest",
        status_code=422,
        details={"errors": [msg]},
    )


async def fetch_package_manifest(url: str, sha256: str) -> PluginManifest:
    """
    @brief Download the package, verify ``sha256`` and parse its manifest.
    @param url https package URL.
    @param sha256 Expected hex digest of the tarball.
    @raises AppError ``package_sha256_mismatch``, ``invalid_manifest`` and download errors.
    """
    if not SHA256_RE.fullmatch(sha256):
        raise _fail("invalid_sha256", "SHA-256 must be 64 hex characters")
    data = await download_package(url)
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), sha256.lower()):
        raise _fail("package_sha256_mismatch", "Package checksum does not match")
    text = await asyncio.to_thread(read_manifest_from_tar, data)
    return parse_manifest(text)
