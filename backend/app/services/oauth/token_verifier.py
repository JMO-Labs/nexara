"""
@file token_verifier.py
@brief ID token verification and claim extraction for OAuth/OIDC.

Verifies JWT id_tokens using provider JWKS and extracts claims
using provider-specific claim mappings.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog
from authlib.jose import JsonWebKey, JsonWebToken

from app.core.exceptions import AuthenticationError
from app.models.oauth_provider import OAuthProvider
from app.services.oauth.user_provisioner import OAuthAuthResult

logger = structlog.get_logger(__name__)

_JWKS_CACHE: dict[str, tuple[dict[str, Any], float]] = {}
"""@brief Module-level JWKS cache: jwks_uri -> (jwks_dict, timestamp)."""
_JWKS_TTL = 3600


async def _fetch_jwks(jwks_uri: str) -> dict[str, Any]:
    """
    @brief Fetch JWKS from URI (cached).

    @param jwks_uri JWKS endpoint URL.
    @return JWKS dict.
    """
    now = time.monotonic()
    if jwks_uri in _JWKS_CACHE:
        cached, ts = _JWKS_CACHE[jwks_uri]
        if now - ts < _JWKS_TTL:
            return cached
        del _JWKS_CACHE[jwks_uri]
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_uri)
        resp.raise_for_status()
        jwks: dict[str, Any] = resp.json()
    _JWKS_CACHE[jwks_uri] = (jwks, now)
    return jwks


async def verify_id_token(id_token: str, provider: OAuthProvider) -> dict[str, Any]:
    """
    @brief Verify and decode an OIDC id_token.

    If provider has jwks_uri: fetch JWKS, verify signature with authlib.
    If no jwks_uri: decode without verification (log warning).

    @param id_token Raw id_token string.
    @param provider OAuth provider config.
    @return Decoded claims dict.
    @raises AuthenticationError If verification fails.
    """
    try:
        if provider.jwks_uri:
            jwks_data = await _fetch_jwks(provider.jwks_uri)
            jwks = JsonWebKey.import_key_set(jwks_data)
            jwt = JsonWebToken(["RS256", "ES256"])
            raw_claims = jwt.decode(id_token, jwks)
            if hasattr(raw_claims, "validate"):
                raw_claims.validate()
            decoded: dict[str, Any] = dict(raw_claims)
            return decoded
        from authlib.jose import jwt as authlib_jwt

        logger.warning("oauth_id_token_no_jwks", provider_slug=getattr(provider, "slug", "?"))
        raw_claims = authlib_jwt.decode(id_token, options={"verify_signature": False})
        result: dict[str, Any] = dict(raw_claims)
        return result
    except Exception as exc:
        raise AuthenticationError(
            message="Invalid OIDC id_token",
            details={"error": str(exc)},
        ) from exc


def extract_claims(claims: dict[str, Any], provider: OAuthProvider) -> OAuthAuthResult:
    """
    @brief Extract OAuthAuthResult from id_token claims using provider mapping.

    @param claims Decoded id_token claims.
    @param provider OAuth provider with claim name config.
    @return OAuthAuthResult with sub, email, name, groups, avatar.
    """
    sub_claim = getattr(provider, "sub_claim", "sub") or "sub"
    email_claim = getattr(provider, "email_claim", "email") or "email"
    name_claim = getattr(provider, "name_claim", "name") or "name"
    group_claim = getattr(provider, "group_claim", "groups") or "groups"
    avatar_claim = getattr(provider, "avatar_claim", "picture") or "picture"

    def _get(key: str, default: Any = None) -> Any:
        val = claims.get(key)
        return val if val is not None else default

    groups_raw = _get(group_claim)
    if isinstance(groups_raw, list):
        groups = [str(g) for g in groups_raw]
    elif groups_raw is not None:
        groups = [str(groups_raw)]
    else:
        groups = []

    return OAuthAuthResult(
        sub=str(_get(sub_claim, "")),
        email=_get(email_claim),
        display_name=_get(name_claim),
        avatar_url=_get(avatar_claim),
        groups=groups,
        raw_claims=claims,
    )
