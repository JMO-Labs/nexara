"""
@file client_ip.py
@brief Single trusted client-IP extraction for audit logs and sign-in records.
"""

from __future__ import annotations

from fastapi import Request


def client_ip(request: Request) -> str | None:
    """
    @brief Best-effort client IP behind our own reverse proxy.

    Uses the right-most X-Forwarded-For entry (appended by our nginx via
    ``$proxy_add_x_forwarded_for``, so a client cannot spoof it), else
    X-Real-IP, else the socket peer.

    @param request Current request.
    @return IP string or None.
    """
    # ponytail: rightmost hop only; PR6 adds TRUSTED_PROXIES to walk past an outer reverse proxy
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        last = fwd.split(",")[-1].strip()
        if last:
            return last
    real = request.headers.get("x-real-ip")
    if real and real.strip():
        return real.strip()
    return request.client.host if request.client else None
