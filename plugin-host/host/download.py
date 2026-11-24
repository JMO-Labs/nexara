"""
@file
@brief SSRF-guarded package download: https only, every hop resolved and checked
       against non-public ranges, connection pinned to the vetted IP, size and time capped.
"""

import asyncio
import ipaddress
import socket

import httpx

from host.errors import InstallError

MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
MAX_REDIRECTS = 5
DOWNLOAD_DEADLINE_S: float = 300
_REDIRECTS = {301, 302, 303, 307, 308}


async def _resolve(host: str) -> list[str]:
    """@brief All addresses for `host` (A + AAAA)."""
    infos = await asyncio.get_running_loop().getaddrinfo(
        host, 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
    )
    return [str(i[4][0]) for i in infos]


def _public(addr: str) -> bool:
    """@brief True only for globally routable unicast (rejects private, loopback,
    link-local, CGNAT, ULA, multicast, reserved, unspecified, IPv4-mapped private)."""
    ip = ipaddress.ip_address(addr.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


async def _vetted_ip(url: httpx.URL) -> str:
    """@brief Resolve the URL host; every address must be public. @return first address."""
    if url.scheme != "https" or not url.host:
        raise InstallError("download_failed")
    try:
        addrs = [str(ipaddress.ip_address(url.host))]
    except ValueError:
        try:
            addrs = await _resolve(url.host)
        except OSError as e:
            raise InstallError("download_failed") from e
    if not addrs:
        raise InstallError("download_failed")
    if not all(_public(a) for a in addrs):
        raise InstallError("download_blocked")
    return addrs[0]


async def _fetch(client: httpx.AsyncClient, url: httpx.URL) -> bytes:
    for _ in range(MAX_REDIRECTS + 1):
        ip = await _vetted_ip(url)
        req = client.build_request(
            "GET",
            url.copy_with(host=ip),
            headers={"Host": url.netloc.decode("ascii")},
            extensions={"sni_hostname": url.host},
        )
        r = await client.send(req, stream=True)
        try:
            if r.status_code in _REDIRECTS and "location" in r.headers:
                url = url.join(r.headers["location"])
                continue
            if r.status_code != 200:
                raise InstallError("download_failed")
            try:
                declared = int(r.headers.get("content-length") or 0)
            except ValueError as e:
                raise InstallError("download_failed") from e
            if declared > MAX_DOWNLOAD_BYTES:
                raise InstallError("package_too_large")
            buf = bytearray()
            async for chunk in r.aiter_bytes():
                buf += chunk
                if len(buf) > MAX_DOWNLOAD_BYTES:
                    raise InstallError("package_too_large")
            return bytes(buf)
        finally:
            await r.aclose()
    raise InstallError("download_failed")


async def fetch(url: str) -> bytes:
    """
    @brief Download `url` (https only, ≤MAX_DOWNLOAD_BYTES, ≤DOWNLOAD_DEADLINE_S overall).
    @return Package bytes (decoded size is what the cap counts).
    """
    try:
        target = httpx.URL(url)
    except (httpx.InvalidURL, TypeError) as e:
        raise InstallError("download_failed") from e
    try:
        async with asyncio.timeout(DOWNLOAD_DEADLINE_S):
            async with httpx.AsyncClient(
                follow_redirects=False, timeout=60, trust_env=False
            ) as client:
                return await _fetch(client, target)
    except (httpx.HTTPError, TimeoutError, ValueError) as e:
        raise InstallError("download_failed") from e
