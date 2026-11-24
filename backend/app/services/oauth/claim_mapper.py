"""
@file claim_mapper.py
@brief Map provider ID-token claims to Nexara user fields via claim_mapping.
"""

from __future__ import annotations

from typing import Any

from app.core.exceptions import AuthenticationError

from .user_provisioner import OAuthAuthResult

_VERIFIED = (True, "true")

DEFAULT_MAPPING: dict[str, str] = {
    "sub": "sub",
    "email": "email",
    "name": "name",
    "picture": "picture",
    "groups": "groups",
}
"""@brief Nexara field -> provider claim path (dotted for nested claims)."""


def _lookup(claims: dict[str, Any], path: str) -> Any:
    """@brief Resolve a dotted claim path; exact key match wins."""
    if path in claims:
        return claims[path]
    cur: Any = claims
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def map_claims(
    claims: dict[str, Any],
    claim_mapping: dict[str, Any] | None,
    username_claim: str | None = "preferred_username",
) -> OAuthAuthResult:
    """
    @brief Transform provider claims into an OAuthAuthResult.

    @param claims Verified ID token claims.
    @param claim_mapping Nexara field -> provider claim overrides (merged over defaults).
    @param username_claim Provider claim (dotted path) holding the username.
    @return OAuthAuthResult (sub, email, display_name, avatar_url, groups).
    @raises AuthenticationError when no subject resolves (mapped or standard `sub`).
    """
    overrides = {k: v for k, v in (claim_mapping or {}).items() if isinstance(v, str)}
    m = {**DEFAULT_MAPPING, **overrides}

    def get(field: str) -> Any:
        return _lookup(claims, m[field])

    raw_groups = get("groups")
    if isinstance(raw_groups, list):
        groups = [str(g) for g in raw_groups]
    elif isinstance(raw_groups, str) and raw_groups:
        groups = [raw_groups]
    else:
        groups = []
    sub = get("sub") or claims.get("sub")
    if not sub:
        raise AuthenticationError(message="OAuth identity missing subject")
    email, name, pic = get("email"), get("name"), get("picture")
    uname = _lookup(claims, username_claim) if username_claim else None
    return OAuthAuthResult(
        sub=str(sub),
        email=str(email) if email else None,
        display_name=str(name) if name else None,
        avatar_url=str(pic) if pic else None,
        groups=groups,
        email_verified=_lookup(claims, "email_verified") in _VERIFIED,
        username=str(uname) if uname else None,
    )
