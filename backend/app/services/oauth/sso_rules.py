"""
@file sso_rules.py
@brief SSO sign-in gates (allowed domains, required group) and username helpers.
"""

from __future__ import annotations

import re
import secrets
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.repositories.user_repo import UserRepository

USERNAME_MAX = 30


def gate_refusal(provider: Any, email: str | None, groups: list[str] | None) -> str | None:
    """
    @brief Evaluate the provider's domain and group gates.

    @param provider OAuthProvider (allowed_domains, required_group).
    @param email Email claimed by the IdP (None fails a domain gate).
    @param groups Group claims.
    @return Refusal code (sso_domain_not_allowed / sso_group_required) or None.
    """
    domains = provider.allowed_domains or []
    if domains:
        domain = email.rsplit("@", 1)[1].strip().lower() if email and "@" in email else ""
        if domain not in domains:
            return "sso_domain_not_allowed"
    required = provider.required_group
    if required and required not in (groups or []):
        return "sso_group_required"
    return None


def clean_username(raw: str | None) -> str | None:
    """
    @brief Reduce a claimed username to the URL-safe charset.

    @param raw Claim value.
    @return Cleaned name (max 30 chars) or None when nothing usable remains.
    """
    if not raw:
        return None
    clean = re.sub(r"[^a-zA-Z0-9_-]", "", str(raw).replace(" ", "_"))[:USERNAME_MAX]
    return clean or None


async def unique_username(
    users: UserRepository,
    base: str,
    self_id: uuid.UUID | None = None,
    exclude: set[str] | None = None,
) -> str:
    """
    @brief First free name among base, base-2, base-3, ...

    A name already held by ``self_id`` counts as free (no churn on re-login).

    @param users User repository.
    @param base Cleaned username.
    @param self_id The user being synced (None on create).
    @param exclude Names to skip (lost an insert race).
    @return Available username.
    """
    for n in range(1, 100):
        suffix = "" if n == 1 else f"-{n}"
        candidate = base[: USERNAME_MAX - len(suffix)] + suffix
        if exclude and candidate in exclude:
            continue
        owner = await users.username_owner_id(candidate)  # incl. soft-deleted
        if owner is not None:
            if owner == self_id:
                return candidate
            continue
        if not await users.username_exists(candidate):  # pet/household @handles
            return candidate
    return f"{base[:21]}_{secrets.token_hex(4)}"
