"""@file webhook_guard.py
@brief SSRF guard for outbound webhook deliveries.

Checked at delivery time (not only on subscription create) so DNS rebinding
cannot redirect a previously valid hostname at internal infrastructure.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

import httpx


async def resolve_host(host: str, port: int) -> list[str]:
    """
    @brief Resolve a hostname to its IP address strings.
    @param host Hostname or IP literal.
    @param port Target port.
    @return Resolved addresses.
    @raises httpx.ConnectError when resolution fails (retryable).
    """
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as exc:
        raise httpx.ConnectError(f"cannot resolve {host}: {exc}") from exc
    return [str(info[4][0]) for info in infos]


def _is_global(addr: str) -> bool:
    """@brief True only for publicly routable addresses (scope id stripped)."""
    try:
        ip = ipaddress.ip_address(addr.split("%", 1)[0])
    except ValueError:
        return False
    mapped = getattr(ip, "ipv4_mapped", None)
    return bool((mapped or ip).is_global)


async def is_blocked_destination(url: str, allowed_hosts: frozenset[str]) -> bool:
    """
    @brief Decide whether a webhook URL targets a non-public address.
    @param url Subscription URL.
    @param allowed_hosts Lower-cased hostnames exempt from the check (opt-in).
    @return True when any resolved address is not globally routable.
    @raises httpx.ConnectError when the host cannot be resolved.
    """
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if not host or parts.scheme not in ("http", "https"):
        return True
    if host in allowed_hosts:
        return False
    port = parts.port or (443 if parts.scheme == "https" else 80)
    addrs = await resolve_host(host, port)
    return not addrs or not all(_is_global(a) for a in addrs)
