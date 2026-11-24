"""
@file test_client_ip.py
@brief client_ip takes the right-most X-Forwarded-For hop.
"""

from types import SimpleNamespace

from app.core.client_ip import client_ip


def _req(headers: dict[str, str], host: str | None = "9.9.9.9"):
    return SimpleNamespace(headers=headers, client=SimpleNamespace(host=host) if host else None)


def test_rightmost_xff_wins_and_spoofed_leftmost_ignored():
    assert client_ip(_req({"x-forwarded-for": "1.2.3.4, 10.0.0.9"})) == "10.0.0.9"
    assert client_ip(_req({"x-forwarded-for": "6.6.6.6"})) == "6.6.6.6"


def test_falls_back_to_real_ip_then_peer():
    assert client_ip(_req({"x-real-ip": "5.5.5.5"})) == "5.5.5.5"
    assert client_ip(_req({})) == "9.9.9.9"
    assert client_ip(_req({}, host=None)) is None
