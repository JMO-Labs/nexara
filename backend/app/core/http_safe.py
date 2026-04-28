"""@file http_safe.py
@brief SSRF-resistant HTTP fetcher for ingesting external URLs (e.g. iCal feeds).
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx


class UnsafeUrlError(ValueError):
    """Raised when a URL targets a disallowed host or scheme."""


_ALLOWED_SCHEMES = {"http", "https"}
_MAX_REDIRECTS = 3


def _validate_host(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"DNS resolution failed for {host!r}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise UnsafeUrlError(f"Disallowed IP {ip} for host {host!r}")


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"Disallowed scheme {parsed.scheme!r}")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("Missing host")
    _validate_host(host)
    return url


async def safe_fetch(
    url: str,
    *,
    timeout: float = 30.0,
    max_bytes: int = 10 * 1024 * 1024,
) -> bytes:
    """Fetch a URL with SSRF protection. Manual redirect handling, validate every hop."""
    current = _validate_url(url)
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        limits=httpx.Limits(max_connections=10),
    ) as client:
        for _ in range(_MAX_REDIRECTS + 1):
            resp = await client.get(current)
            if resp.is_redirect:
                loc = resp.headers.get("location")
                if not loc:
                    raise UnsafeUrlError("Redirect without Location header")
                current = _validate_url(loc)
                continue
            content = resp.content[:max_bytes]
            return content
        raise UnsafeUrlError("Too many redirects")
