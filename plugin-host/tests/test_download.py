"""
@file
@brief Download tests: https-only, size cap, SSRF guard on every hop, deadline.
"""

import asyncio

import httpx
import pytest
import respx

from host import download
from host.download import fetch
from host.installer import InstallError

PUBLIC = "93.184.216.34"
URL = "https://pkgs.example.com/p.tgz"
IP_URL = f"https://{PUBLIC}/p.tgz"


@pytest.fixture
def dns(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    """@brief Fake resolver: hostname -> addresses (default public)."""
    table: dict[str, list[str]] = {"pkgs.example.com": [PUBLIC], "cdn.example.com": [PUBLIC]}

    async def resolve(host: str) -> list[str]:
        return table[host]

    monkeypatch.setattr(download, "_resolve", resolve)
    return table


async def code_of(url: str) -> str:
    with pytest.raises(InstallError) as e:
        await fetch(url)
    return e.value.code


async def test_connects_to_vetted_ip_with_original_host(dns: dict) -> None:
    with respx.mock:
        route = respx.get(IP_URL).mock(return_value=httpx.Response(200, content=b"abc"))
        assert await fetch(URL) == b"abc"
    req = route.calls.last.request
    assert req.headers["host"] == "pkgs.example.com"
    assert req.extensions["sni_hostname"] == "pkgs.example.com"


async def test_http_rejected(dns: dict) -> None:
    assert await code_of("http://pkgs.example.com/p.tgz") == "download_failed"


@pytest.mark.parametrize(
    "addr",
    [
        "127.0.0.1",
        "10.0.0.5",
        "172.17.0.2",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "::1",
        "fd00::1",
        "fe80::1",
        "224.0.0.1",
        "0.0.0.0",
        "::ffff:127.0.0.1",
    ],
)
async def test_private_addresses_rejected(dns: dict, addr: str) -> None:
    dns["pkgs.example.com"] = [addr]
    assert await code_of(URL) == "download_blocked"


@pytest.mark.parametrize(
    "addr",
    [
        "::a00:1",
        "::7f00:1",
        "::ffff:0:a00:1",
        "64:ff9b::a00:1",
        "64:ff9b::7f00:1",
        "64:ff9b::5db8:d822",
        "64:ff9b:1::1",
        "2002:a00:1::1",
        "2002:5db8:d822::1",
        "2001::1",
        "2001:0:4136:e378:8000:63bf:3fff:fdd2",
    ],
    ids=[
        "v4compat-priv",
        "v4compat-lo",
        "siit",
        "nat64-priv",
        "nat64-lo",
        "nat64-public",
        "nat64-local",
        "6to4-priv",
        "6to4-public",
        "teredo",
        "teredo-2",
    ],
)
async def test_ipv6_translation_ranges_rejected(dns: dict, addr: str) -> None:
    dns["pkgs.example.com"] = [addr]
    assert await code_of(URL) == "download_blocked"


@pytest.mark.parametrize(
    "addr", ["fec0::1", "fc00::1", "4000::1", "100::1", "2001:db8::1", "ff02::1", "3fff::1"]
)
def test_ipv6_outside_global_unicast_rejected(addr: str) -> None:
    assert not download._public(addr)


def test_public_ipv6_allowed() -> None:
    assert download._public("2606:4700::6810:84e5")
    assert download._public(PUBLIC)


async def test_any_private_address_rejects(dns: dict) -> None:
    dns["pkgs.example.com"] = [PUBLIC, "10.0.0.1"]
    assert await code_of(URL) == "download_blocked"


async def test_ip_literal_private_rejected(dns: dict) -> None:
    assert await code_of("https://127.0.0.1/p.tgz") == "download_blocked"
    assert await code_of("https://[::1]/p.tgz") == "download_blocked"


async def test_redirect_chain_checked_each_hop(dns: dict) -> None:
    dns["internal.example.com"] = ["10.1.2.3"]
    with respx.mock:
        respx.get(IP_URL).mock(
            return_value=httpx.Response(301, headers={"location": "https://cdn.example.com/a"})
        )
        respx.get(f"https://{PUBLIC}/a").mock(
            return_value=httpx.Response(302, headers={"location": "https://internal.example.com/b"})
        )
        assert await code_of(URL) == "download_blocked"


async def test_redirect_chain_to_http_rejected(dns: dict) -> None:
    with respx.mock:
        respx.get(IP_URL).mock(
            return_value=httpx.Response(301, headers={"location": "https://cdn.example.com/a"})
        )
        respx.get(f"https://{PUBLIC}/a").mock(
            return_value=httpx.Response(302, headers={"location": "http://cdn.example.com/b"})
        )
        assert await code_of(URL) == "download_failed"


async def test_redirect_followed(dns: dict) -> None:
    with respx.mock:
        respx.get(IP_URL).mock(return_value=httpx.Response(302, headers={"location": "/real.tgz"}))
        respx.get(f"https://{PUBLIC}/real.tgz").mock(return_value=httpx.Response(200, content=b"x"))
        assert await fetch(URL) == b"x"


async def test_too_many_redirects(dns: dict) -> None:
    with respx.mock:
        respx.get(IP_URL).mock(return_value=httpx.Response(302, headers={"location": "/p.tgz"}))
        assert await code_of(URL) == "download_failed"


async def test_size_cap(dns: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(download, "MAX_DOWNLOAD_BYTES", 10)
    with respx.mock:
        respx.get(IP_URL).mock(return_value=httpx.Response(200, content=b"x" * 11))
        assert await code_of(URL) == "package_too_large"


async def test_bad_content_length(dns: dict) -> None:
    with respx.mock:
        respx.get(IP_URL).mock(
            return_value=httpx.Response(200, headers={"content-length": "nan"}, content=b"")
        )
        assert await code_of(URL) == "download_failed"


async def test_non_200(dns: dict) -> None:
    with respx.mock:
        respx.get(IP_URL).mock(return_value=httpx.Response(404))
        assert await code_of(URL) == "download_failed"


async def test_overall_deadline(dns: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(download, "DOWNLOAD_DEADLINE_S", 0.05)

    async def slow(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(200)

    with respx.mock:
        respx.get(IP_URL).mock(side_effect=slow)
        assert await code_of(URL) == "download_failed"


async def test_unresolvable(dns: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail(host: str) -> list[str]:
        raise OSError("nxdomain")

    monkeypatch.setattr(download, "_resolve", fail)
    assert await code_of(URL) == "download_failed"


async def test_insecure_flag_off_by_default(dns: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLUGIN_HOST_ALLOW_INSECURE_DOWNLOADS", "false")
    assert await code_of("http://pkgs.example.com/p.tgz") == "download_failed"
    assert await code_of("https://127.0.0.1/p.tgz") == "download_blocked"


async def test_insecure_flag_allows_http_and_private(
    dns: dict, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("PLUGIN_HOST_ALLOW_INSECURE_DOWNLOADS", "true")
    dns["pkgs.example.com"] = ["10.0.0.5"]
    with respx.mock:
        respx.get("http://10.0.0.5/p.tgz").respond(200, content=b"ok")
        with caplog.at_level("WARNING", logger="plugin_host"):
            assert await fetch("http://pkgs.example.com/p.tgz") == b"ok"
    assert "INSECURE download" in caplog.text
