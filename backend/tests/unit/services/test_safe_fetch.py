"""
@file test_safe_fetch.py
@brief SSRF defenses: schemes/ports, public-only addresses, per-hop redirect
       checks, connect-time pinning (DNS rebinding), size caps.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from app.services import safe_fetch
from app.services.safe_fetch import UnsafeURLError, _PinnedBackend, is_public_ip, safe_get

DNS = {
    "shop.example": ["93.184.216.34"],
    "cdn.example": ["93.184.216.35"],
    "internal.example": ["10.0.0.7"],
    "metadata.example": ["169.254.169.254"],
}


def fake_resolve(host: str) -> list[str]:
    if host not in DNS:
        raise OSError("nxdomain")
    return DNS[host]


def mock(handler):
    return httpx.MockTransport(handler)


@pytest.mark.parametrize(
    ("ip", "ok"),
    [
        ("93.184.216.34", True),
        ("2606:4700::1111", True),
        ("10.1.2.3", False),
        ("172.16.0.1", False),
        ("192.168.0.1", False),
        ("127.0.0.1", False),
        ("169.254.169.254", False),
        ("100.64.0.1", False),
        ("0.0.0.0", False),
        ("224.0.0.1", False),
        ("::1", False),
        ("fe80::1", False),
        ("fd00::1", False),
        ("::ffff:10.0.0.1", False),
        ("::ffff:93.184.216.34", True),
        ("64:ff9b::a9fe:a9fe", False),  # NAT64 -> 169.254.169.254
        ("64:ff9b::5db8:d822", True),  # NAT64 -> public
        ("2002:7f00:1::1", False),  # 6to4 -> 127.0.0.1
        ("2002:5db8:d822::1", False),  # 6to4 refused outright
        ("2001:0:4136:e378:8000:63bf:f5ff:fffe", False),  # Teredo -> 10.0.0.1 client
        ("::7f00:1", False),  # IPv4-compatible 127.0.0.1
        ("::5db8:d822", False),  # IPv4-compatible public: still refused
        ("64:ff9b:1::5db8:d822", False),  # local-use NAT64 refused
        ("2001:0:5db8:d822::1", False),  # Teredo refused
        ("not-an-ip", False),
    ],
)
def test_is_public_ip(ip, ok):
    assert is_public_ip(ip) is ok


async def test_fetches_public_page_with_cap():
    t = mock(
        lambda r: httpx.Response(200, headers={"content-type": "text/html"}, content=b"<p>hi</p>")
    )
    got = await safe_get(
        "https://shop.example/p", max_bytes=100, resolver=fake_resolve, transport=t
    )
    assert got is not None and got.body == b"<p>hi</p>" and got.content_type == "text/html"


@pytest.mark.parametrize(
    "url",
    [
        "ftp://shop.example/",
        "file:///etc/passwd",
        "https://shop.example:8080/",
        "https://u:p@shop.example/",
        "http://internal.example/",
        "http://metadata.example/latest/meta-data/",
        "http://nowhere.example/",
    ],
)
async def test_refuses_unsafe_urls_without_request(url):
    called = []
    t = mock(lambda r: called.append(r) or httpx.Response(200))
    assert await safe_get(url, max_bytes=100, resolver=fake_resolve, transport=t) is None
    assert called == []


async def test_redirect_to_internal_host_is_blocked():
    seen = []

    def handler(r: httpx.Request) -> httpx.Response:
        seen.append(r.url.host)
        return httpx.Response(302, headers={"location": "http://internal.example/admin"})

    got = await safe_get(
        "https://shop.example/", max_bytes=100, resolver=fake_resolve, transport=mock(handler)
    )
    assert got is None and seen == ["shop.example"]


async def test_redirect_to_public_host_is_followed_relative_too():
    def handler(r: httpx.Request) -> httpx.Response:
        if r.url.path == "/start":
            return httpx.Response(301, headers={"location": "/next"})
        if r.url.host == "shop.example":
            return httpx.Response(302, headers={"location": "https://cdn.example/img"})
        return httpx.Response(200, headers={"content-type": "image/png"}, content=b"PNG")

    got = await safe_get(
        "https://shop.example/start", max_bytes=100, resolver=fake_resolve, transport=mock(handler)
    )
    assert got is not None and got.url == "https://cdn.example/img"


async def test_redirect_loop_gives_up():
    t = mock(lambda r: httpx.Response(302, headers={"location": "https://shop.example/again"}))
    assert (
        await safe_get("https://shop.example/", max_bytes=100, resolver=fake_resolve, transport=t)
        is None
    )


async def test_size_and_type_limits():
    big = mock(
        lambda r: httpx.Response(200, headers={"content-type": "text/html"}, content=b"x" * 500)
    )
    assert (
        await safe_get("https://shop.example/", max_bytes=100, resolver=fake_resolve, transport=big)
        is None
    )
    lying = mock(
        lambda r: httpx.Response(
            200, headers={"content-type": "text/html", "content-length": "999999"}, content=b"x"
        )
    )
    assert (
        await safe_get(
            "https://shop.example/", max_bytes=100, resolver=fake_resolve, transport=lying
        )
        is None
    )
    svg = mock(
        lambda r: httpx.Response(200, headers={"content-type": "image/svg+xml"}, content=b"<svg/>")
    )
    got = await safe_get(
        "https://shop.example/",
        max_bytes=100,
        accept=lambda ct: ct != "image/svg+xml",
        resolver=fake_resolve,
        transport=svg,
    )
    assert got is None
    gz = mock(
        lambda r: httpx.Response(
            200, headers={"content-type": "text/html", "content-encoding": "gzip"}, content=b"x"
        )
    )
    assert (
        await safe_get("https://shop.example/", max_bytes=100, resolver=fake_resolve, transport=gz)
        is None
    )
    err = mock(lambda r: httpx.Response(500))
    assert (
        await safe_get("https://shop.example/", max_bytes=100, resolver=fake_resolve, transport=err)
        is None
    )


async def test_pinned_backend_rechecks_at_connect_and_dials_the_checked_ip():
    """DNS rebinding: an answer that turns private at connect time is refused."""
    answers = iter([["10.0.0.9"]])
    backend = _PinnedBackend(lambda _h: next(answers))
    backend._inner = AsyncMock()
    with pytest.raises(UnsafeURLError):
        await backend.connect_tcp("shop.example", 443)
    backend._inner.connect_tcp.assert_not_awaited()

    backend = _PinnedBackend(fake_resolve)
    backend._inner = AsyncMock()
    await backend.connect_tcp("shop.example", 443, timeout=5)
    assert backend._inner.connect_tcp.await_args.args[:2] == ("93.184.216.34", 443)


def test_pinned_transport_uses_pinned_backend():
    t = safe_fetch.pinned_transport(fake_resolve)
    assert isinstance(t._pool._network_backend, _PinnedBackend)  # noqa: SLF001
