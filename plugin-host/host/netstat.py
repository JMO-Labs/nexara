"""
@file
@brief Minimal /proc/net/tcp{,6} reader: who listens on a local port.

Plugins share the host's network namespace, so another plugin could bind a port the
supervisor handed out. The proxy forwards only when every listener that can accept a
connection to 127.0.0.1:<port> belongs to the plugin's uid (the kernel refuses a second
such bind from another uid). Binds on other addresses (127.0.0.2, ::1, …) are ignored,
so they cannot be used to block another plugin's events.
"""

from pathlib import Path

PROC_NET = Path("/proc/net")
_LISTEN = "0A"
# local_address hex (as printed by the kernel) of sockets that accept 127.0.0.1 traffic
_REACHES_LOOPBACK = {
    "tcp": {"0100007F", "00000000"},  # 127.0.0.1, 0.0.0.0
    "tcp6": {"0" * 32, "0000000000000000FFFF00000100007F"},  # [::], [::ffff:127.0.0.1]
}


def _sockets() -> list[tuple[str, str, int, int]]:
    """@brief (table, local ip hex, port, uid) of every LISTEN TCP socket."""
    out: list[tuple[str, str, int, int]] = []
    for name in ("tcp", "tcp6"):
        try:
            lines = (PROC_NET / name).read_text().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            f = line.split()
            if len(f) > 7 and f[3] == _LISTEN:
                ip, port = f[1].rsplit(":", 1)
                out.append((name, ip.upper(), int(port, 16), int(f[7])))
    return out


def listeners() -> list[tuple[int, int]]:
    """@brief (port, uid) of every LISTEN socket on any address (for port allocation)."""
    return [(port, uid) for _, _, port, uid in _sockets()]


def listener_uids(port: int) -> list[int]:
    """
    @brief Owner uids of the listeners on `port` that a connection to 127.0.0.1 can reach
    (empty: none). If an IPv4 listener (127.0.0.1 / 0.0.0.0) exists it receives the
    connection, and any `[::]` entry beside it must be v6only (a dual-stack one would have
    failed with EADDRINUSE), so IPv6 entries count only when there is no IPv4 listener.
    """
    hits = [(t, uid) for t, ip, p, uid in _sockets() if p == port and ip in _REACHES_LOOPBACK[t]]
    v4 = [uid for t, uid in hits if t == "tcp"]
    return v4 or [uid for _, uid in hits]
