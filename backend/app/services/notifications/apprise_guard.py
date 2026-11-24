"""@file apprise_guard.py
@brief SSRF guard for Apprise URLs (checked on create/test and again at send time).

The URL is parsed exactly as the sender parses it (``Apprise().add``). Every
endpoint host the plugin will connect to must resolve to a global address unless
``allow_local``. Members' sends also have HTTP redirects disabled.
"""

from __future__ import annotations

import ipaddress
import socket

import apprise
from apprise import AppriseAsset

from app.core.exceptions import AppError
from app.core.i18n import _

#: Schemes whose ``host`` attribute is a credential token, not a network host;
#: they talk to a fixed public API.
TOKEN_HOST_SCHEMES = frozenset({"tgram", "discord", "pover"})
_NAT64 = ipaddress.ip_network("64:ff9b::/96")


def _blocked(addr: str) -> bool:
    """@brief True unless ``addr`` (and anything embedded in it) is globally routable."""
    ip = ipaddress.ip_address(addr.split("%", 1)[0])
    inner: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = [ip]
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            inner.append(ip.ipv4_mapped)
        if ip.sixtofour:
            inner.append(ip.sixtofour)
        if ip in _NAT64:
            inner.append(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF))
    return any(not i.is_global or i.is_multicast for i in inner)


def build_apprise(url: str, *, allow_local: bool) -> apprise.Apprise:
    """
    @brief Build the sender for ``url``; redirects are off unless ``allow_local``.

    A URL ``?redirect=`` param overrides the asset default, so the flag is forced
    on each plugin after parsing.
    """
    apobj = apprise.Apprise(asset=AppriseAsset(http_redirects=allow_local))
    apobj.add(url)
    if not allow_local:
        for plugin in apobj:
            plugin.redirects = False
    return apobj


def _endpoint_hosts(plugin: object) -> list[str] | None:
    """@return Hosts the plugin connects to, or None if a required host is missing."""
    hosts: list[str] = []
    tokens = getattr(plugin, "template_tokens", None) or {}
    schema = str(getattr(plugin, "protocol", "") or getattr(plugin, "schema", "")).lower()
    names = {n for n in dir(plugin) if n.endswith("_host") and not n.startswith("_")}
    if "host" in tokens and schema not in TOKEN_HOST_SCHEMES:
        names.add("host")
        if not getattr(plugin, "host", None):
            return None
    for n in names:
        v = getattr(plugin, n, None)
        if isinstance(v, str) and v:
            hosts.append(v)
    return hosts


def _fail() -> AppError:
    return AppError(
        code="apprise_url_blocked",
        message=_("Apprise URL points to a private or unresolvable address"),
        status_code=422,
    )


def check_apprise_url(url: str, *, allow_local: bool) -> None:
    """
    @brief Reject Apprise URLs that target non-public hosts.

    @param url Plain Apprise URL.
    @param allow_local Skip all checks (admin targets / community opt-in).
    @raises AppError ``apprise_url_blocked`` (422) on a private host, an unparsable
        URL, a missing host, or a name that cannot be resolved.
    """
    if allow_local:
        return
    try:
        plugins = list(build_apprise(url, allow_local=False))
    except Exception:
        raise _fail() from None
    if len(plugins) != 1:
        raise _fail()
    hosts = _endpoint_hosts(plugins[0])
    if hosts is None:
        raise _fail()
    for host in hosts:
        host = host.strip("[]")
        try:
            infos = socket.getaddrinfo(host, None)
            bad = not infos or any(_blocked(str(i[4][0])) for i in infos)
        except (socket.gaierror, UnicodeError, ValueError):
            bad = True  # cannot verify
        if bad:
            raise _fail()
