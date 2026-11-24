"""
@file policy.py
@brief Second-factor policy for every login path.

Decides which second factors a sign-in must present, and which community
``require_2fa`` claims an access token carries so ``get_current_user`` can
enforce enrolment from the token alone (no extra query per request).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.core.exceptions import AppError
from app.core.i18n import _
from app.repositories.passkey_repo import PasskeyRepository
from app.repositories.two_factor_repo import TwoFactorRepository
from app.services.auth.two_factor import GRACE

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

SETUP_PREFIXES = ("/api/v1/auth/2fa/", "/api/v1/auth/passkeys/register/")
"""@brief Routes still reachable once the grace period has ended without a factor."""
SETUP_PATHS = frozenset({"/api/v1/users/me", "/api/v1/auth/logout"})


async def factor_methods(session: AsyncSession, user: User) -> list[str]:
    """
    @brief Second factors the user can complete a login with.

    Any registered passkey counts as a factor (no opt-out). Recovery codes only
    exist alongside TOTP.

    @return Subset of ``["totp", "recovery", "passkey"]``; empty = no 2nd factor.
    """
    methods = ["totp", "recovery"] if user.totp_enabled else []
    if await PasskeyRepository(session, user.community_id).count_for_user(user.id):
        methods.append("passkey")
    return methods


async def second_factor_needed(session: AsyncSession, user: User) -> bool:
    """@brief True when a password / magic-link login must be completed with a 2nd factor."""
    return bool(await factor_methods(session, user))


async def setup_claims(session: AsyncSession, user: User) -> dict[str, Any]:
    """
    @brief Access-token claims for a member the ``require_2fa`` policy covers but who has no factor.

    SSO-only users (no password) are never covered. A missing grace clock is
    started now so the deadline cannot keep sliding.

    @return ``{"twofa_setup_required": True, "grace_until": <epoch>}`` or ``{}``.
    """
    if user.password_hash is None:
        return {}
    policy = await TwoFactorRepository(session).get_policy(user.community_id)
    covered = policy == "everyone" or (policy == "admins" and user.role == "admin")
    if not covered or await second_factor_needed(session, user):
        return {}
    if user.two_factor_required_since is None:
        user.two_factor_required_since = datetime.now(UTC)
    deadline = user.two_factor_required_since + GRACE
    return {"twofa_setup_required": True, "grace_until": int(deadline.timestamp())}


def enforce_setup(payload: dict[str, Any], path: str) -> None:
    """
    @brief Block a token past its 2FA grace period outside the enrolment allowlist.

    @param payload Decoded access-token claims.
    @param path Request path (``/api/v1/...``).
    @raises AppError 403 ``2fa_setup_required``.
    """
    if not payload.get("twofa_setup_required"):
        return
    if time.time() < float(payload.get("grace_until") or 0):
        return
    if path in SETUP_PATHS or path.startswith(SETUP_PREFIXES):
        return
    raise AppError(
        code="2fa_setup_required",
        message=_("Set up two-factor authentication to continue"),
        status_code=403,
    )
