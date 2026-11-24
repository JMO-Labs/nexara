"""
@file test_client_ip.py
@brief client_ip believes forwarding headers only from TRUSTED_PROXIES.
"""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from starlette.datastructures import Headers

from app.core import client_ip as mod
from app.core.client_ip import client_ip
from app.core.config import Settings


def _req(headers: dict[str, str], host: str | None = "127.0.0.1"):
    return SimpleNamespace(
        headers=Headers(headers), client=SimpleNamespace(host=host) if host else None
    )


@pytest.fixture
def settings(monkeypatch):
    def use(**kw):
        s = Settings(SECRET_KEY="test", **kw)
        monkeypatch.setattr(mod, "get_settings", lambda: s)
        return s

    use()
    return use


def test_untrusted_peer_ignores_spoofed_xff(settings):
    assert client_ip(_req({"x-forwarded-for": "6.6.6.6"}, host="9.9.9.9")) == "9.9.9.9"


def test_trusted_peer_stops_at_first_untrusted_hop(settings):
    assert client_ip(_req({"x-forwarded-for": "1.2.3.4, 10.0.0.9"})) == "10.0.0.9"


def test_trusted_outer_proxy_walked_past(settings):
    settings(TRUSTED_PROXIES="127.0.0.1/32,10.0.0.0/8")
    assert client_ip(_req({"x-forwarded-for": "1.2.3.4, 10.0.0.9"})) == "1.2.3.4"


def test_spoofed_leftmost_beyond_untrusted_hop_ignored(settings):
    settings(TRUSTED_PROXIES="127.0.0.1/32,10.0.0.0/8")
    assert client_ip(_req({"x-forwarded-for": "6.6.6.6, 1.2.3.4, 10.0.0.9"})) == "1.2.3.4"


def test_all_trusted_chain_returns_leftmost(settings):
    settings(TRUSTED_PROXIES="127.0.0.1/32,192.168.0.0/16")
    assert client_ip(_req({"x-forwarded-for": "192.168.1.5, 192.168.1.1"})) == "192.168.1.5"


def test_junk_hop_keeps_last_good_hop(settings):
    settings(TRUSTED_PROXIES="127.0.0.1/32,10.0.0.0/8")
    assert client_ip(_req({"x-forwarded-for": "1.2.3.4, junk, 10.0.0.9"})) == "10.0.0.9"


def test_real_ip_only_without_xff_and_trusted_peer(settings):
    assert client_ip(_req({"x-real-ip": "5.5.5.5"})) == "5.5.5.5"
    assert client_ip(_req({"x-real-ip": "5.5.5.5", "x-forwarded-for": "7.7.7.7"})) == "7.7.7.7"
    assert client_ip(_req({"x-real-ip": "5.5.5.5"}, host="9.9.9.9")) == "9.9.9.9"


def test_cf_header_needs_flag_and_trusted_peer(settings):
    h = {"cf-connecting-ip": "1.2.3.4", "x-forwarded-for": "8.8.8.8"}
    assert client_ip(_req(h)) == "8.8.8.8"
    settings(CF_ACCESS_ENABLED=True)
    assert client_ip(_req(h)) == "1.2.3.4"
    assert client_ip(_req(h, host="9.9.9.9")) == "9.9.9.9"


def test_ipv4_mapped_peer_is_trusted(settings):
    assert client_ip(_req({"x-forwarded-for": "1.2.3.4"}, host="::ffff:127.0.0.1")) == "1.2.3.4"


def test_non_ip_peer_returned_unchanged(settings):
    assert client_ip(_req({"x-forwarded-for": "1.2.3.4"}, host="testclient")) == "testclient"


def test_no_headers_and_no_peer(settings):
    assert client_ip(_req({})) == "127.0.0.1"
    assert client_ip(_req({}, host=None)) is None


def test_invalid_trusted_proxies_rejected_at_load():
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY="test", TRUSTED_PROXIES="127.0.0.1,nope")
