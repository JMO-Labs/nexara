"""
@file profile_sync.py
@brief Per-login SSO profile sync (name, email, avatar, username) and role audit.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_repo import AuditRepository
from app.services.oauth.email_change import notify_email_synced
from app.services.oauth.sso_rules import clean_username, unique_username

if TYPE_CHECKING:
    from app.models.user import User
    from app.repositories.user_repo import UserRepository
    from app.services.oauth.user_provisioner import OAuthAuthResult


async def sync_profile(
    users: UserRepository,
    user: User,
    auth: OAuthAuthResult,
    *,
    session: AsyncSession,
    community_id: uuid.UUID,
    provider_id: uuid.UUID | None,
) -> None:
    """
    @brief Copy IdP profile fields onto the user when they changed.

    Email is only taken when the IdP verified it and no other user holds it;
    a change is audited, old-address credentials revoked and the old address told.

    @param users User repository.
    @param user Linked user.
    @param auth Mapped claims (username from the provider's username_claim).
    @param session Request session (audit, token revocation).
    @param community_id Community (notice branding).
    @param provider_id Provider driving the sync.
    """
    old_email = user.email
    updates: dict[str, Any] = {}
    if auth.display_name and auth.display_name != user.display_name:
        updates["display_name"] = auth.display_name
    if auth.avatar_url and auth.avatar_url != user.avatar_url:
        updates["avatar_url"] = auth.avatar_url
    if auth.email and auth.email_verified:
        email = auth.email.strip().lower()
        if email != (user.email or "").lower():
            if await users.email_owner_id(email) is None:  # incl. soft-deleted
                updates["email"] = email
                updates["email_verified"] = True
    base = clean_username(auth.username)
    if base and base != user.username:
        name = await unique_username(users, base, user.id)
        if name != user.username:
            updates["username"] = name
    if updates:
        await users.update(user, updates)
    if "email" in updates:
        await notify_email_synced(
            session,
            user_id=user.id,
            community_id=community_id,
            provider_id=provider_id,
            old_email=old_email,
            new_email=updates["email"],
        )


async def audit_role_synced(
    session: AsyncSession,
    user_id: uuid.UUID,
    old_role: str,
    new_role: str,
    *,
    provider_id: uuid.UUID | str | None = None,
) -> None:
    """
    @brief Audit an SSO group-driven community role change (actor = system).

    @param session Request session.
    @param user_id Target user.
    @param old_role Role before sync.
    @param new_role Role after sync.
    @param provider_id Provider that drove the change.
    """
    await AuditRepository(session).append(
        actor_id=None,
        action="sso.role_synced",
        target_type="user",
        target_id=user_id,
        extra_data={
            "old_role": old_role,
            "new_role": new_role,
            "provider_id": str(provider_id) if provider_id else None,
        },
    )
