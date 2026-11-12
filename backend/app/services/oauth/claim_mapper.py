"""
@file claim_mapper.py
@brief Map provider ID-token claims to Nexara user fields via claim_mapping.
"""

from __future__ import annotations

from typing import Any

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


def map_claims(claims: dict[str, Any], claim_mapping: dict[str, str] | None) -> OAuthAuthResult:
    """
    @brief Transform provider claims into an OAuthAuthResult.

    @param claims Verified ID token claims.
    @param claim_mapping Nexara field -> provider claim overrides (merged over defaults).
    @return OAuthAuthResult (sub, email, display_name, avatar_url, groups).
    """
    m = {**DEFAULT_MAPPING, **(claim_mapping or {})}

    def get(field: str) -> Any:
        return _lookup(claims, m[field])

    raw_groups = get("groups")
    if isinstance(raw_groups, list):
        groups = [str(g) for g in raw_groups]
    elif isinstance(raw_groups, str) and raw_groups:
        groups = [raw_groups]
    else:
        groups = []
    email, name, pic = get("email"), get("name"), get("picture")
    return OAuthAuthResult(
        sub=str(get("sub") or ""),
        email=str(email) if email else None,
        display_name=str(name) if name else None,
        avatar_url=str(pic) if pic else None,
        groups=groups,
        email_verified=_lookup(claims, "email_verified") in _VERIFIED,
    )
