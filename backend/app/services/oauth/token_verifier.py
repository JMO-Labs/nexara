"""
@file token_verifier.py
@brief OIDC ID token verification and claim extraction.

Uses authlib for JWKS fetching and JWT verification. Caches JWKS per URI.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Any, cast

import httpx
import structlog
from authlib.jose import JsonWebKey, JsonWebToken

from app.core.exceptions import AuthenticationError

from .user_provisioner import OAuthAuthResult

if TYPE_CHECKING:
    from app.models.oauth_provider import OAuthProvider

logger = structlog.get_logger(__name__)

_JWKS_CACHE: dict[str, dict[str, Any]] = {}
"""@brief Module-level cache for JWKS by URI."""


async def _fetch_jwks(jwks_uri: str) -> dict[str, Any]:
    """
    @brief Fetch JWKS from URI with caching.

    @param jwks_uri URL of the JWKS endpoint.
    @return JWKS dict (keys, etc.).
    """
    if jwks_uri in _JWKS_CACHE:
        return _JWKS_CACHE[jwks_uri]
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_uri)
        resp.raise_for_status()
        jwks = cast(dict[str, Any], resp.json())
    _JWKS_CACHE[jwks_uri] = jwks
    return jwks


def _get_claim(claims: dict[str, Any], key: str | None, fallback: str) -> Any:
    """@brief Get claim by key or fallback."""
    if key and key in claims:
        return claims.get(key)
    return claims.get(fallback)


async def verify_id_token(
    id_token: str,
    provider: OAuthProvider,
    nonce: str | None = None,
) -> dict[str, Any]:
    """
    @brief Verify OIDC ID token signature (JWKS), expiry and nonce.

    Providers without a jwks_uri are rejected: unsigned tokens are never accepted.
    The exp claim is mandatory and checked against the current time.

    @param id_token Raw ID token JWT string.
    @param provider OAuth provider with jwks_uri (and optional issuer).
    @param nonce Expected nonce; when given the token's nonce must match.
    @return Verified claims dict.
    @raises AuthenticationError If verification fails.
    """
    try:
        jwks_uri = getattr(provider, "jwks_uri", None)
        if not jwks_uri:
            raise AuthenticationError(message="Provider has no jwks_uri")
        jwks = await _fetch_jwks(jwks_uri)
        key_set = JsonWebKey.import_key_set(jwks)
        options: dict[str, Any] = {
            "aud": {"essential": False},
            "exp": {"essential": True},
        }
        issuer = getattr(provider, "issuer", None)
        if isinstance(issuer, str) and issuer:
            options["iss"] = {"essential": True, "value": issuer}
        claims = JsonWebToken(["RS256", "ES256"]).decode(
            id_token, key_set, claims_options=options
        )
        if hasattr(claims, "validate"):
            claims.validate()
        result = dict(claims)
        if nonce is not None and not secrets.compare_digest(
            str(result.get("nonce", "")), nonce
        ):
            raise AuthenticationError(message="Invalid OIDC id_token nonce")
        return result
    except AuthenticationError:
        raise
    except Exception as exc:
        raise AuthenticationError(message="Invalid OIDC id_token") from exc


def extract_claims(
    claims: dict[str, Any],
    provider: OAuthProvider,
) -> OAuthAuthResult:
    """
    @brief Extract sub, email, display_name, avatar_url, groups from claims.

    Uses provider's claim mapping (sub_claim, email_claim, etc.).

    @param claims Verified ID token claims.
    @param provider OAuth provider with claim mappings.
    @return OAuthAuthResult with extracted values.
    """
    sub = str(_get_claim(claims, getattr(provider, "sub_claim", None), "sub") or "")
    email = _get_claim(claims, getattr(provider, "email_claim", None), "email")
    display_name = _get_claim(claims, getattr(provider, "name_claim", None), "name")
    avatar_url = _get_claim(claims, getattr(provider, "avatar_claim", None), "picture")

    group_claim = getattr(provider, "group_claim", "groups")
    groups_raw = _get_claim(claims, group_claim, "groups")
    if isinstance(groups_raw, list):
        groups = [str(g) for g in groups_raw]
    elif isinstance(groups_raw, str):
        groups = [groups_raw]
    else:
        groups = []

    return OAuthAuthResult(
        sub=sub,
        email=str(email) if email else None,
        display_name=str(display_name) if display_name else None,
        avatar_url=str(avatar_url) if avatar_url else None,
        groups=groups,
    )
