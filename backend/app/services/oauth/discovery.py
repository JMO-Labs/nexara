"""
@file discovery.py
@brief OpenID Connect discovery for OAuth provider endpoints.

Fetches .well-known/openid-configuration and validates issuer URL
to prevent SSRF (rejects http, localhost, private IPs).
"""

from __future__ import annotations

import ipaddress
import time
from typing import Any, TypedDict, cast
from urllib.parse import urlparse

import httpx


def _is_disallowed_host(hostname: str) -> bool:
    """
    @brief Check if hostname is disallowed (localhost or private IP).

    @param hostname Hostname or IP string.
    @return True if disallowed (localhost, 127.0.0.1, 10.x, 192.168.x, 172.16-31.x).
    """
    if not hostname:
        return True
    lower = hostname.lower().strip()
    if lower in ("localhost",):
        return True
    try:
        ip = ipaddress.ip_address(lower)
        return ip.is_loopback or ip.is_private
    except ValueError:
        return False


class DiscoveryEndpoints(TypedDict, total=False):
    """@brief OIDC discovery document endpoints."""

    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str
    end_session_endpoint: str


async def discover_endpoints(issuer: str) -> DiscoveryEndpoints:
    """
    @brief Fetch OIDC discovery document and extract endpoints.

    Rejects http:// (must be https), localhost, and private IPs.
    Validates required authorization_endpoint is present.

    @param issuer OIDC issuer URL (e.g. https://accounts.google.com).
    @return Dict with authorization_endpoint, token_endpoint, etc.
    @raises ValueError If scheme is not https or host is disallowed.
    """
    parsed = urlparse(issuer)
    if parsed.scheme != "https":
        raise ValueError("Issuer must use https scheme")
    host = parsed.hostname or ""
    if _is_disallowed_host(host):
        raise ValueError("Issuer host is disallowed (localhost or private IP)")

    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    auth_endpoint = data.get("authorization_endpoint")
    if not auth_endpoint:
        raise ValueError("Required field authorization_endpoint is missing")

    return DiscoveryEndpoints(
        authorization_endpoint=auth_endpoint,
        token_endpoint=data.get("token_endpoint"),
        userinfo_endpoint=data.get("userinfo_endpoint"),
        jwks_uri=data.get("jwks_uri"),
        end_session_endpoint=data.get("end_session_endpoint"),
    )


CACHE_TTL_SECONDS = 24 * 3600
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
"""@brief discovery_url -> (fetched_at monotonic, document)."""


def clear_cache() -> None:
    """@brief Drop all cached discovery documents."""
    _CACHE.clear()


def _validate_https_public(url: str, what: str) -> None:
    """@brief Require https and a non-private host. @raises ValueError otherwise."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"{what} must use https scheme")
    if _is_disallowed_host(parsed.hostname or ""):
        raise ValueError(f"{what} host is disallowed (localhost or private IP)")


async def fetch_discovery(discovery_url: str, timeout: float = 10.0) -> dict[str, Any]:
    """
    @brief Fetch an OIDC discovery document from its full URL, cached 24h.

    @param discovery_url e.g. https://kc.example.com/.well-known/openid-configuration.
    @param timeout HTTP timeout in seconds.
    @return Discovery document (issuer, authorization_endpoint, token_endpoint, jwks_uri...).
    @raises ValueError If URL/issuer is not https/public or required fields are missing.
    """
    _validate_https_public(discovery_url, "Discovery URL")
    hit = _CACHE.get(discovery_url)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(discovery_url)
        resp.raise_for_status()
        doc = cast(dict[str, Any], resp.json())
    _validate_https_public(str(doc.get("issuer", "")), "Issuer")
    if not doc.get("authorization_endpoint") or not doc.get("token_endpoint"):
        raise ValueError("Discovery document missing authorization/token endpoint")
    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri", "userinfo_endpoint"):
        if doc.get(key):
            _validate_https_public(str(doc[key]), key)
    _CACHE[discovery_url] = (time.monotonic(), doc)
    return doc
