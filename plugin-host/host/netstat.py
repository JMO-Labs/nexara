"""
@file
@brief Minimal /proc/net/tcp{,6} reader: who listens on a local port.

Plugins share the host's network namespace, so another plugin could bind a port the
supervisor handed out. The proxy forwards only when every listener belongs to the
plugin's uid (the kernel refuses a second bind on a held port from another uid).
"""

from pathlib import Path

PROC_NET = Path("/proc/net")
_LISTEN = "0A"


def listeners() -> list[tuple[int, int]]:
    """@brief (port, uid) of every LISTEN TCP socket, IPv4 and IPv6."""
    out: list[tuple[int, int]] = []
    for name in ("tcp", "tcp6"):
        try:
            lines = (PROC_NET / name).read_text().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            f = line.split()
            if len(f) > 7 and f[3] == _LISTEN:
                out.append((int(f[1].rsplit(":", 1)[1], 16), int(f[7])))
    return out


def listener_uids(port: int) -> list[int]:
    """@brief Owner uids of the LISTEN sockets on `port` (empty: nobody listens)."""
    return [uid for p, uid in listeners() if p == port]
