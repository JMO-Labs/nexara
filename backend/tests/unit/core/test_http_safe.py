import pytest

from app.core.http_safe import UnsafeUrlError, safe_fetch


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost/",
        "http://10.0.0.1/",
        "http://169.254.169.254/",
        "file:///etc/passwd",
        "ftp://x/",
    ],
)
async def test_blocks_unsafe(url: str) -> None:
    with pytest.raises(UnsafeUrlError):
        await safe_fetch(url)


# --- pinning / redirects / deadline -------------------------------------------

import asyncio  # noqa: E402
from unittest.mock import patch  # noqa: E402

import httpx  # noqa: E402

from app.core.http_safe import _fetch, _pin  # noqa: E402

PUBLIC = [(2, 1, 6, "", ("93.184.216.34", 0))]
PRIVATE = [(2, 1, 6, "", ("10.0.0.5", 0))]


def test_pin_rewrites_to_vetted_ip_and_keeps_host() -> None:
    with patch("socket.getaddrinfo", return_value=PUBLIC):
        pinned, host_header, sni = _pin("https://img.example.com:8443/a.png?x=1")
    assert pinned == "https://93.184.216.34:8443/a.png?x=1"
    assert host_header == "img.example.com:8443"
    assert sni == "img.example.com"


def test_pin_rejects_if_any_address_private() -> None:
    with (
        patch("socket.getaddrinfo", return_value=PUBLIC + PRIVATE),
        pytest.raises(UnsafeUrlError),
    ):
        _pin("https://mixed.example.com/")


async def test_fetch_connects_to_ip_and_blocks_redirect_to_private() -> None:
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(302, headers={"location": "http://internal.example/x"})

    answers = iter([PUBLIC, PRIVATE])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with (
            patch("socket.getaddrinfo", side_effect=lambda *a: next(answers)),
            pytest.raises(UnsafeUrlError),
        ):
            await _fetch(client, "http://good.example/a", 100)
    assert seen[0].url.host == "93.184.216.34"
    assert seen[0].headers["host"] == "good.example"


async def test_fetch_caps_body() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 5000)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with patch("socket.getaddrinfo", return_value=PUBLIC):
            assert await _fetch(client, "http://good.example/a", 100) == b"x" * 100


async def test_total_deadline() -> None:
    async def slow(*_a: object, **_k: object) -> bytes:
        await asyncio.sleep(5)
        return b""

    with patch("app.core.http_safe._fetch", slow), pytest.raises(TimeoutError):
        await safe_fetch("http://good.example/", timeout=0.05)
