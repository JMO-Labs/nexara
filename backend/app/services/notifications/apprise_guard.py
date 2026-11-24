"""@file apprise_guard.py
@brief SSRF guard for Apprise URLs (checked on create/test and again at send time).

Schemes without a host (``tgram://``, ``discord://`` ...) talk to fixed public APIs
and pass. Host-bearing schemes (``json://``, ``ntfy://`` ...) must resolve to
public addresses unless ``allow_local`` is set.
"""

from __future__ import annotations

import ipaddress
import socket

import apprise

from app.core.exceptions import AppError
from app.core.i18n import _


def _blocked(addr: str) -> bool:
    ip = ipaddress.ip_address(addr.split("%", 1)[0])
    ip = getattr(ip, "ipv4_mapped", None) or ip
    return bool(
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
    )


def _hosts(url: str) -> list[str]:
    plugin = apprise.Apprise.instantiate(url)
    if not plugin:
        return []
    plugins = plugin if isinstance(plugin, list) else [plugin]
    # Only plugins whose URL schema has a ``host`` token (json://, ntfy://); others
    # (tgram://) reuse the ``host`` attribute for tokens and hit fixed public APIs.
    return [
        h
        for p in plugins
        if "host" in (getattr(p, "template_tokens", None) or {}) and (h := getattr(p, "host", None))
    ]


def check_apprise_url(url: str, *, allow_local: bool) -> None:
    """
    @brief Reject Apprise URLs that target non-public hosts.

    @param url Plain Apprise URL.
    @param allow_local Skip all checks (admin targets / community opt-in).
    @raises AppError ``apprise_url_blocked`` (422) on a private host or unresolvable name.
    """
    if allow_local:
        return
    for host in _hosts(url):
        try:
            infos = socket.getaddrinfo(host, None)
            bad = any(_blocked(str(i[4][0])) for i in infos)
        except (socket.gaierror, UnicodeError, ValueError):
            bad = True  # cannot verify
        if bad:
            raise AppError(
                code="apprise_url_blocked",
                message=_("Apprise URL points to a private or unresolvable address"),
                status_code=422,
            )
