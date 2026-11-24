"""
@file client_ip.py
@brief Single trusted client-IP extraction for audit logs, rate limits and WAF.
"""

from __future__ import annotations

import ipaddress

from fastapi import Request

from app.core.config import get_settings

_IP = ipaddress.IPv4Address | ipaddress.IPv6Address


def _ip(value: str | None) -> _IP | None:
    """@brief Parse an IP (unwrapping IPv4-mapped IPv6); None when unparseable."""
    if not value:
        return None
    try:
        ip = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        return ip.ipv4_mapped
    return ip


def _trusted(ip: _IP) -> bool:
    """@brief True when ``ip`` is inside TRUSTED_PROXIES."""
    return any(ip in net for net in get_settings().trusted_proxy_networks)


def client_ip(request: Request) -> str | None:
    """
    @brief Real client IP, believing forwarding headers only from trusted proxies.

    An untrusted (or non-IP) peer is returned as-is. From a trusted peer:
    CF-Connecting-IP when CF_ACCESS_ENABLED, else walk X-Forwarded-For
    (or X-Real-IP) right to left and return the first untrusted hop; an
    all-trusted chain yields the leftmost valid hop.

    @param request Current request.
    @return IP string or None.
    """
    peer = request.client.host if request.client else None
    if peer is None:
        return None
    p = _ip(peer)
    if p is None or not _trusted(p):
        return peer
    headers = request.headers
    if get_settings().CF_ACCESS_ENABLED and (cf := _ip(headers.get("cf-connecting-ip"))):
        return str(cf)
    xff = ",".join(headers.getlist("x-forwarded-for"))
    hops = [h.strip() for h in xff.split(",") if h.strip()]
    if not hops and (real := headers.get("x-real-ip")):
        hops = [real.strip()]
    addr = peer
    for h in reversed(hops):
        ip = _ip(h)
        if ip is None:
            break
        addr = str(ip)
        if not _trusted(ip):
            break
    return addr
