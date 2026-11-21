"""@file http_safe.py
@brief SSRF-resistant HTTP fetcher for ingesting external URLs (iCal feeds,
       image links). Every hop: resolve once, reject non-public addresses,
       then connect to that exact IP (Host header + TLS SNI keep the name),
       so DNS rebinding cannot swap in an internal address. One total
       deadline covers all hops and the body; the body is capped in bytes.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse, urlunparse

import httpx


class UnsafeUrlError(ValueError):
    """Raised when a URL targets a disallowed host or scheme."""


_ALLOWED_SCHEMES = {"http", "https"}
_MAX_REDIRECTS = 3


def _resolve_public(host: str) -> str:
    """
    @brief Resolve ``host`` and return one address, refusing if ANY is non-public.
    @raises UnsafeUrlError on DNS failure or a private/loopback/etc. address.
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"DNS resolution failed for {host!r}") from exc
    ips = [ipaddress.ip_address(info[4][0]) for info in infos]
    for ip in ips:
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise UnsafeUrlError(f"Disallowed IP {ip} for host {host!r}")
    if not ips:
        raise UnsafeUrlError(f"No address for {host!r}")
    return str(ips[0])


def _pin(url: str) -> tuple[str, str, str]:
    """
    @brief Validate ``url`` and rewrite it to connect to the vetted IP.
    @return (pinned_url, host_header, hostname)
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"Disallowed scheme {parsed.scheme!r}")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("Missing host")
    ip = _resolve_public(host)
    ip_netloc = f"[{ip}]" if ":" in ip else ip
    if parsed.port:
        ip_netloc += f":{parsed.port}"
    host_header = host + (f":{parsed.port}" if parsed.port else "")
    return urlunparse(parsed._replace(netloc=ip_netloc)), host_header, host


async def _fetch(client: httpx.AsyncClient, url: str, max_bytes: int) -> bytes:
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        pinned, host_header, hostname = _pin(current)
        req = client.build_request(
            "GET",
            pinned,
            headers={"Host": host_header},
            extensions={"sni_hostname": hostname},
        )
        resp = await client.send(req, stream=True)
        try:
            if resp.is_redirect:
                loc = resp.headers.get("location")
                if not loc:
                    raise UnsafeUrlError("Redirect without Location header")
                current = urljoin(current, loc)
                continue
            buf = bytearray()
            async for chunk in resp.aiter_bytes():
                buf += chunk
                if len(buf) >= max_bytes:
                    break
            return bytes(buf[:max_bytes])
        finally:
            await resp.aclose()
    raise UnsafeUrlError("Too many redirects")


async def safe_fetch(
    url: str,
    *,
    timeout: float = 30.0,
    max_bytes: int = 10 * 1024 * 1024,
) -> bytes:
    """
    @brief Fetch a public URL with SSRF protection.
    @param timeout Total seconds for all hops and the body (not per read).
    @param max_bytes Body cap; the result is truncated there.
    @raises UnsafeUrlError for disallowed targets; TimeoutError past the deadline.
    """
    async with (
        asyncio.timeout(timeout),
        httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,  # proxies from env must not route around the check
            limits=httpx.Limits(max_connections=10),
        ) as client,
    ):
        return await _fetch(client, url, max_bytes)
