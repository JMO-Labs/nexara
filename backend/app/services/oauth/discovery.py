"""
@file discovery.py
@brief OIDC discovery: fetch openid-configuration with SSRF protection.

Fetches the .well-known/openid-configuration document from an OIDC issuer
and returns the standard endpoints. Rejects private/local URLs to prevent SSRF.
"""

from __future__ import annotations

import ipaddress
from typing import TypedDict
from urllib.parse import urlparse

import httpx


class DiscoveryEndpoints(TypedDict, total=False):
    """@brief Typed dict for OIDC discovery endpoint keys."""

    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str | None
    end_session_endpoint: str | None


_REQUIRED_KEYS = ("authorization_endpoint", "token_endpoint", "userinfo_endpoint", "jwks_uri")
_OPTIONAL_KEYS = ("end_session_endpoint",)


def _is_disallowed_host(hostname: str) -> bool:
    """
    @brief Check if hostname is localhost or private IP (SSRF protection).

    @param hostname Parsed hostname from issuer URL.
    @return True if the host should be rejected.
    """
    lower = hostname.lower()
    if lower in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback
    except ValueError:
        pass
    return False


async def discover_endpoints(issuer_url: str) -> dict:
    """
    @brief Fetch OIDC discovery document and return endpoint URLs.

    @param issuer_url Base issuer URL (e.g. https://idp.example.com).
    @return Dict with authorization_endpoint, token_endpoint, userinfo_endpoint,
            jwks_uri, end_session_endpoint (optional, may be None).
    @raises ValueError If scheme is not https, host is private/local, or
            response is missing required fields.
    @raises httpx.RequestError On network failure.
    @raises httpx.HTTPStatusError On non-2xx response.
    """
    parsed = urlparse(issuer_url)
    if parsed.scheme != "https":
        raise ValueError("OIDC discovery requires https scheme")
    hostname = parsed.hostname or ""
    if _is_disallowed_host(hostname):
        raise ValueError("OIDC discovery disallowed for private or localhost hosts")

    discovery_url = issuer_url.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient() as client:
        resp = await client.get(discovery_url)
        resp.raise_for_status()
        data = resp.json()

    for key in _REQUIRED_KEYS:
        if key not in data or not data[key]:
            raise ValueError(f"OIDC discovery missing required field: {key}")

    result: DiscoveryEndpoints = {
        "authorization_endpoint": data["authorization_endpoint"],
        "token_endpoint": data["token_endpoint"],
        "userinfo_endpoint": data["userinfo_endpoint"],
        "jwks_uri": data.get("jwks_uri"),
    }
    result["end_session_endpoint"] = data.get("end_session_endpoint")
    return result
