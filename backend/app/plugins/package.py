"""
@file package.py
@brief Download a plugin package tarball, verify its sha256 and read its manifest.

The tarball is never extracted: only ``nexara-plugin.toml`` at the archive root is
read in memory, with caps on download size, member count and bytes walked.
"""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import hmac
import io
import re
import tarfile
import time
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.http_safe import UnsafeUrlError, safe_fetch
from app.plugins.manifest import MAX_MANIFEST_BYTES, PluginManifest, parse_manifest

MAX_PACKAGE_BYTES = 50 * 1024 * 1024
MAX_MEMBERS = 10_000
MAX_WALK_BYTES = 64 * 1024 * 1024  # decompressed bytes (headers included) read at most
MAX_EXT_HEADER = 64 * 1024  # GNU long-name/link and PAX header payloads
MAX_EXT_CHAIN = 4  # consecutive extended headers before one member
_EXT_TYPES = frozenset(
    {tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK, tarfile.XHDTYPE, tarfile.XGLTYPE,
     tarfile.SOLARIS_XHDTYPE}
)  # fmt: skip
CACHE_TTL = 600.0
CACHE_MAX = 32
_cache: dict[tuple[str, str], tuple[float, PluginManifest]] = {}
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


class _UnsafeArchiveError(Exception):
    """@brief Archive exceeded a cap while being read."""


class _CappedReader(io.RawIOBase):
    """@brief Stream that fails once more than ``cap`` decompressed bytes were read."""

    def __init__(self, inner: gzip.GzipFile, cap: int) -> None:
        self._inner, self._left = inner, cap

    def readable(self) -> bool:
        return True

    def read(self, size: int | None = -1) -> bytes:
        if size is None or size < 0 or size > self._left + 1:
            size = self._left + 1
        data = self._inner.read(size)
        self._left -= len(data)
        if self._left < 0:
            raise _UnsafeArchiveError("archive too large")
        return data


class _GuardedInfo(tarfile.TarInfo):
    """
    @brief Header guards that run before CPython reads extended-header payloads.

    Rejects oversized GNU long-name / PAX headers, chains of more than
    ``MAX_EXT_CHAIN`` extended headers (CPython recurses per header) and every GNU sparse
    format (the 1.0 map is unbounded). Hooks private ``TarInfo`` methods; checked against
    CPython 3.12 (3.12.12). The bomb regression tests fail loudly if the hooks stop firing.
    """

    def _proc_member(self, tf: tarfile.TarFile) -> tarfile.TarInfo:
        if self.type == tarfile.GNUTYPE_SPARSE:
            raise _UnsafeArchiveError("sparse members are not allowed")
        if self.type in _EXT_TYPES:
            chain = getattr(tf, "_nx_ext_chain", 0) + 1
            if self.size > MAX_EXT_HEADER or chain > MAX_EXT_CHAIN:
                raise _UnsafeArchiveError("extended header too large")
            tf._nx_ext_chain = chain  # type: ignore[attr-defined]
        else:
            tf._nx_ext_chain = 0  # type: ignore[attr-defined]
        info: tarfile.TarInfo = super()._proc_member(tf)  # type: ignore[misc]
        return info

    def _proc_sparse(self, *_: object) -> tarfile.TarInfo:
        raise _UnsafeArchiveError("sparse members are not allowed")

    def _proc_gnusparse_00(self, *_: object) -> None:
        raise _UnsafeArchiveError("sparse members are not allowed")

    def _proc_gnusparse_01(self, *_: object) -> None:
        raise _UnsafeArchiveError("sparse members are not allowed")

    def _proc_gnusparse_10(self, *_: object) -> None:
        raise _UnsafeArchiveError("sparse members are not allowed")

    def _apply_pax_info(self, pax_headers: dict[str, str], *args: object) -> None:
        if any(k.startswith("GNU.sparse.") for k in pax_headers):
            raise _UnsafeArchiveError("sparse members are not allowed")
        super()._apply_pax_info(pax_headers, *args)  # type: ignore[misc]


def read_manifest_from_tar(data: bytes) -> str:
    """
    @brief Return the text of ``nexara-plugin.toml`` at the root of a .tar.gz, in one
        streaming pass without extracting. Decompressed bytes, member count and extended
        header sizes are capped (decompression-bomb guard).
    @raises AppError ``invalid_manifest`` if missing, not a regular file, too large, or the
        archive is unreadable or unsafe.
    """
    try:
        with (
            gzip.GzipFile(fileobj=io.BytesIO(data)) as gz,
            tarfile.open(
                fileobj=_CappedReader(gz, MAX_WALK_BYTES), mode="r|", tarinfo=_GuardedInfo
            ) as tf,
        ):
            for n, member in enumerate(tf):
                if n >= MAX_MEMBERS:
                    break
                if member.name.removeprefix("./") != MANIFEST_NAME:
                    continue
                if not member.isreg() or member.size > MAX_MANIFEST_BYTES:
                    raise _invalid("nexara-plugin.toml must be a regular file under 64 KiB")
                fh = tf.extractfile(member)
                if fh is None:
                    raise _invalid("nexara-plugin.toml is unreadable")
                return fh.read(MAX_MANIFEST_BYTES + 1).decode()
    except _UnsafeArchiveError:
        raise _invalid("package archive is too large or unsafe") from None
    except (
        tarfile.TarError,
        EOFError,
        OSError,
        UnicodeDecodeError,
        MemoryError,
        RecursionError,
        ValueError,
    ):
        raise _invalid("package is not a readable .tar.gz archive") from None
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

    Verified manifests are cached per (url, sha256) for 10 min in-process, so the
    scope-approval resubmit does not download the package again.
    @param url https package URL.
    @param sha256 Expected hex digest of the tarball.
    @raises AppError ``package_sha256_mismatch``, ``invalid_manifest`` and download errors.
    """
    if not SHA256_RE.fullmatch(sha256):
        raise _fail("invalid_sha256", "SHA-256 must be 64 hex characters")
    key = (url, sha256.lower())
    hit = _cache.get(key)
    if hit and hit[0] > time.monotonic():  # scope-review round trip: skip the 2nd download
        return hit[1]
    data = await download_package(url)
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), sha256.lower()):
        raise _fail("package_sha256_mismatch", "Package checksum does not match")
    text = await asyncio.to_thread(read_manifest_from_tar, data)
    m = parse_manifest(text)
    now = time.monotonic()
    for k in [k for k, (exp, _) in _cache.items() if exp <= now]:
        del _cache[k]
    if len(_cache) >= CACHE_MAX:
        _cache.pop(next(iter(_cache)))
    _cache[key] = (now + CACHE_TTL, m)
    return m
