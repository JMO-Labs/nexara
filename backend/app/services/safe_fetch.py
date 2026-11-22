"""
@file safe_fetch.py
@brief SSRF-safe HTTP GET for server-side fetches of user-supplied URLs
       (link previews, preview images).

Defenses:
- only http/https on the default ports (80/443);
- every address the host resolves to must be globally routable (blocks
  private, loopback, link-local incl. cloud metadata, CGNAT, multicast,
  reserved, and IPv4-mapped IPv6 forms of those);
- the TCP connection is pinned to an address that passed the check, so a
  DNS answer that changes between check and connect (rebinding) is useless;
- redirects are followed manually (max 3) and every hop is re-checked;
- no proxies from the environment, short timeout, streamed size cap.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import httpcore
import httpx

TIMEOUT = 5.0
MAX_REDIRECTS = 3
ALLOWED_PORTS = {None, 80, 443}
USER_AGENT = "NexaraLinkPreview/1.0"


class UnsafeURLError(Exception):
    """@brief The URL or one of its addresses is not allowed."""


def is_public_ip(ip_str: str) -> bool:
    """@brief Globally routable unicast address (unwraps IPv4-mapped IPv6)."""
    try:
        ip = ipaddress.ip_address(ip_str.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def resolve(host: str) -> list[str]:
    """@brief All addresses for ``host`` (blocking; call via a thread)."""
    infos = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    return list(dict.fromkeys(str(i[4][0]) for i in infos))


async def public_addresses(host: str, resolver: Callable[[str], list[str]] = resolve) -> list[str]:
    """
    @brief Resolve ``host`` and require every address to be public.
    @throws UnsafeURLError when any address is not public or none resolve.
    """
    try:
        addrs = await asyncio.to_thread(resolver, host)
    except (OSError, UnicodeError) as exc:
        raise UnsafeURLError(f"cannot resolve {host}") from exc
    if not addrs or not all(is_public_ip(a) for a in addrs):
        raise UnsafeURLError(f"{host} resolves to a non-public address")
    return addrs


def check_url(url: str) -> str:
    """
    @brief Validate scheme, host and port of a URL (no DNS).
    @return the hostname
    @throws UnsafeURLError on anything other than http(s) on 80/443 with a host.
    """
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise UnsafeURLError("only http(s) URLs with a host are allowed")
    try:
        port = p.port
    except ValueError as exc:
        raise UnsafeURLError("bad port") from exc
    if port not in ALLOWED_PORTS or p.username or p.password:
        raise UnsafeURLError("non-default port or credentials in URL")
    return p.hostname


class _PinnedBackend(httpcore.AsyncNetworkBackend):
    """@brief Resolves and checks at connect time, then dials the checked IP."""

    def __init__(self, resolver: Callable[[str], list[str]]) -> None:
        self._inner = httpcore.AnyIOBackend()
        self._resolver = resolver

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        addrs = await public_addresses(host, self._resolver)
        # TLS SNI and certificate checks still use the original hostname:
        # httpcore passes the origin host to start_tls, not this address.
        return await self._inner.connect_tcp(
            addrs[0],
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(self, *args: Any, **kwargs: Any) -> httpcore.AsyncNetworkStream:
        raise UnsafeURLError("unix sockets are not allowed")

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


def pinned_transport(resolver: Callable[[str], list[str]] = resolve) -> httpx.AsyncHTTPTransport:
    """@brief httpx transport whose connections go only to checked public IPs."""
    transport = httpx.AsyncHTTPTransport(trust_env=False, retries=0)
    # ponytail: httpx has no public hook for the network backend; swap the pool.
    # Revisit if httpx exposes ``network_backend`` (tests pin this behaviour).
    transport._pool = httpcore.AsyncConnectionPool(  # noqa: SLF001
        ssl_context=httpx.create_ssl_context(trust_env=False),
        max_connections=4,
        network_backend=_PinnedBackend(resolver),
    )
    return transport


@dataclass
class Fetched:
    """@brief A capped response body."""

    url: str
    content_type: str
    body: bytes


async def safe_get(
    url: str,
    *,
    max_bytes: int,
    accept: Callable[[str], bool] = lambda _ct: True,
    resolver: Callable[[str], list[str]] = resolve,
    transport: httpx.AsyncBaseTransport | None = None,
) -> Fetched | None:
    """
    @brief GET a user-supplied URL safely.
    @param max_bytes stop (and return None) once the body exceeds this
    @param accept content-type predicate checked before reading the body
    @param resolver DNS resolver (tests inject a fake)
    @param transport override (tests); defaults to the pinned transport
    @return the body, or None when unsafe, rejected, too big or failed
    """
    try:
        async with httpx.AsyncClient(
            transport=transport or pinned_transport(resolver),
            timeout=TIMEOUT,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            for _hop in range(MAX_REDIRECTS + 1):
                await public_addresses(check_url(url), resolver)
                async with client.stream("GET", url) as resp:
                    if resp.is_redirect:
                        loc = resp.headers.get("location")
                        if not loc:
                            return None
                        url = urljoin(url, loc)
                        continue
                    if resp.status_code != 200:
                        return None
                    ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                    declared = resp.headers.get("content-length")
                    if not accept(ctype) or (declared and int(declared) > max_bytes):
                        return None
                    buf = bytearray()
                    async for chunk in resp.aiter_bytes():
                        buf.extend(chunk)
                        if len(buf) > max_bytes:
                            return None
                    return Fetched(url=url, content_type=ctype, body=bytes(buf))
            return None  # too many redirects
    except (UnsafeURLError, httpx.HTTPError, ValueError):
        return None
