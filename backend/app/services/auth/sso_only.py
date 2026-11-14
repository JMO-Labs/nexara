"""
@file sso_only.py
@brief SSO-only enforcement: flag lookup, guard, and toggle logic.

When ``community_branding.sso_only`` is true, password login, registration
and magic-link auth are rejected with 403.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, AuthorizationError
from app.core.i18n import _
from app.models.branding import CommunityBranding
from app.models.oauth_provider import OAuthProvider

SSO_ONLY_WARNING = (
    "Once enabled, ensure an SSO provider is configured. Users cannot log in without it."
)


async def is_sso_only(session: AsyncSession, community_id: uuid.UUID) -> bool:
    """
    @brief Return True when SSO-only mode is enabled for the community.

    @param session Async DB session.
    @param community_id Community UUID.
    """
    stmt = select(CommunityBranding.sso_only).where(CommunityBranding.community_id == community_id)
    return bool((await session.execute(stmt)).scalar_one_or_none())


async def assert_password_auth_allowed(session: AsyncSession, community_id: uuid.UUID) -> None:
    """
    @brief Guard for password/magic-link flows.

    @raises AuthorizationError If SSO-only mode is on.
    """
    if await is_sso_only(session, community_id):
        raise AuthorizationError(message=_("Single sign-on only: password login is disabled"))


async def count_enabled_providers(session: AsyncSession, community_id: uuid.UUID) -> int:
    """@brief Count enabled OAuth/OIDC providers for the community."""
    stmt = (
        select(func.count())
        .select_from(OAuthProvider)
        .where(OAuthProvider.community_id == community_id, OAuthProvider.enabled.is_(True))
    )
    return int((await session.execute(stmt)).scalar_one())


async def write_flag(
    session: AsyncSession, community_id: uuid.UUID, enabled: bool, actor_id: uuid.UUID | None
) -> None:
    """@brief Persist the flag, creating the branding row if missing."""
    res = await session.execute(
        update(CommunityBranding)
        .where(CommunityBranding.community_id == community_id)
        .values(sso_only=enabled, updated_by=actor_id, updated_at=func.now())
    )
    # Result.rowcount exists on CursorResult only
    if res.rowcount == 0:  # type: ignore[attr-defined]
        session.add(CommunityBranding(community_id=community_id, sso_only=enabled))
    await session.flush()


async def set_sso_only(
    session: AsyncSession, community_id: uuid.UUID, enabled: bool, actor_id: uuid.UUID | None
) -> None:
    """
    @brief Toggle SSO-only mode.

    @raises AppError 422 when enabling without an enabled OIDC provider.
    """
    if enabled and await count_enabled_providers(session, community_id) < 1:
        raise AppError(
            code="sso_provider_required",
            message=_("Configure and enable at least one OIDC provider before enabling SSO-only"),
            status_code=422,
        )
    await write_flag(session, community_id, enabled, actor_id)
