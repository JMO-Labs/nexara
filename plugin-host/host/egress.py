"""
@file
@brief Compose-only egress filter: iptables/ip6tables rules in the host's own network
       namespace for packets from plugin uids (owner match; OUTPUT chain).

Plugins may reach the public internet, the Docker DNS resolver (127.0.0.11) and the
resolved NEXARA_URL host:port. Everything else that is local or private is dropped:
loopback (the host control API on 8700, other plugins' ports), RFC1918, CGNAT,
link-local (cloud metadata), and the IPv6 equivalents incl. translation ranges.
Replies on connections the host opened to a plugin (the event proxy) stay allowed via
conntrack. Enabled by PLUGIN_EGRESS_FILTER=true (needs CAP_NET_ADMIN); Helm uses a
NetworkPolicy instead. If enabled and the rules cannot be installed, no plugin starts.
"""

import logging
import os
import socket
import subprocess
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from host.perms import PROBE_UID, UID_BASE

log = logging.getLogger(__name__)

ENV = "PLUGIN_EGRESS_FILTER"
CHAIN = "NEXARA_PLUGIN_OUT"
UID_RANGE = f"{PROBE_UID}-{UID_BASE + 9999}"
DOCKER_DNS = "127.0.0.11"
V4_DROP = (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16",
    "172.16.0.0/12", "192.0.0.0/24", "192.168.0.0/16", "198.18.0.0/15",
    "224.0.0.0/4", "240.0.0.0/4",
)  # fmt: skip
V6_DROP = (
    "::/128", "::1/128", "::ffff:0:0/96", "64:ff9b::/96", "64:ff9b:1::/48", "100::/64",
    "2001::/32", "2002::/16", "fc00::/7", "fe80::/10", "fec0::/10", "ff00::/8",
)  # fmt: skip
IF_INET6 = Path("/proc/net/if_inet6")

Run = Callable[[list[str], str | None], int]


class EgressError(Exception):
    """@brief The filter is enabled but could not be installed."""


def enabled() -> bool:
    return os.environ.get(ENV, "").strip().lower() == "true"


def nexara_targets(url: str | None) -> list[tuple[str, int]]:
    """@brief (ip, port) pairs NEXARA_URL resolves to; [] if unset/unresolvable."""
    if not url:
        return []
    parts = urlsplit(url)
    if not parts.hostname:
        return []
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
    except OSError:
        log.error("egress: cannot resolve NEXARA_URL host; plugins cannot reach Nexara")
        return []
    return sorted({(str(i[4][0]), port) for i in infos})


def ruleset(v6: bool, allow: list[tuple[str, int]]) -> str:
    """@brief iptables-restore input (--noflush) rebuilding CHAIN for one family."""
    fam = [(ip, port) for ip, port in allow if (":" in ip) == v6]
    lines = ["*filter", f":{CHAIN} - [0:0]", f"-F {CHAIN}"]
    lines.append(f"-A {CHAIN} -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT")
    if not v6:
        lines += [f"-A {CHAIN} -d {DOCKER_DNS}/32 -p {p} -j ACCEPT" for p in ("udp", "tcp")]
    plen = 128 if v6 else 32
    lines += [f"-A {CHAIN} -d {ip}/{plen} -p tcp --dport {port} -j ACCEPT" for ip, port in fam]
    lines += [f"-A {CHAIN} -d {net} -j DROP" for net in (V6_DROP if v6 else V4_DROP)]
    lines += [f"-A {CHAIN} -j RETURN", "COMMIT", ""]
    return "\n".join(lines)


def jump_rule() -> list[str]:
    """@brief OUTPUT rule sending plugin-uid packets through CHAIN."""
    return ["OUTPUT", "-m", "owner", "--uid-owner", UID_RANGE, "-j", CHAIN]


def _run(argv: list[str], stdin: str | None) -> int:
    try:
        return subprocess.run(
            argv, input=stdin, capture_output=True, text=True, timeout=30
        ).returncode
    except (OSError, subprocess.SubprocessError):
        return -1


def apply(url: str | None = None, run: Run = _run) -> None:
    """
    @brief (Re)build the rules for IPv4 and, if the kernel has IPv6, IPv6. Idempotent.
    @param url NEXARA_URL (default: host env).
    @raise EgressError on any failure.
    """
    allow = nexara_targets(url if url is not None else os.environ.get("NEXARA_URL"))
    families = [("iptables", False)]
    if IF_INET6.exists():
        families.append(("ip6tables", True))
    for tool, v6 in families:
        if run([f"{tool}-restore", "-w", "--noflush"], ruleset(v6, allow)) != 0:
            raise EgressError(f"{tool}-restore failed")
        if run([tool, "-w", "-C", *jump_rule()], None) != 0:
            if run([tool, "-w", "-I", *jump_rule()[:1], "1", *jump_rule()[1:]], None) != 0:
                raise EgressError(f"{tool} jump rule failed")
    log.info("egress filter installed (nexara targets: %d)", len(allow))
