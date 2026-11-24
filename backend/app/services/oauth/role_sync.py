"""
@file role_sync.py
@brief SSO-driven role and subgroup changes: last-admin guard and audit helpers.

Shared by the provisioner (returning/first link) and the deferred link
(pending_link.create_link) so neither can demote the last admin.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.user_repo import UserRepository

logger = structlog.get_logger(__name__)


async def can_change_role(
    users: UserRepository, community_id: uuid.UUID, user: User, new_role: str
) -> bool:
    """
    @brief False when the change would demote the community's last active admin.

    @param users User repository (request session).
    @param community_id Community scope.
    @param user Target user.
    @param new_role Role SSO wants to apply.
    @return Whether the change is allowed.
    """
    if user.role != "admin" or new_role == "admin":
        return True
    return await users.count_active_admins(community_id) > 1


async def audit_role_sync_skipped(
    session: AsyncSession,
    user_id: uuid.UUID,
    old: str,
    new: str,
    provider_id: uuid.UUID | str | None,
) -> None:
    """
    @brief Log + audit a role sync refused by the last-admin guard.

    @param session Request session.
    @param user_id Target user (the last admin).
    @param old Current role.
    @param new Mapped role that was not applied.
    @param provider_id Provider driving the change.
    """
    logger.warning("sso_role_sync_skipped_last_admin", user_id=str(user_id), new=new)
    await AuditRepository(session).append(
        actor_id=None,
        action="sso.role_sync_skipped",
        target_type="user",
        target_id=user_id,
        extra_data={
            "old": old,
            "new": new,
            "reason": "last_admin",
            "provider_id": str(provider_id) if provider_id else None,
        },
    )


async def audit_subgroups_synced(
    session: AsyncSession,
    user_id: uuid.UUID,
    added: list[uuid.UUID],
    removed: list[uuid.UUID],
    changed: list[uuid.UUID],
    provider_id: uuid.UUID | str | None,
) -> None:
    """
    @brief Audit SSO subgroup membership changes (no-op when nothing changed).

    @param session Request session.
    @param user_id Target user.
    @param added Subgroups joined.
    @param removed Subgroups left.
    @param changed Subgroups whose SSO role changed.
    @param provider_id Provider driving the change.
    """
    if not (added or removed or changed):
        return
    await AuditRepository(session).append(
        actor_id=None,
        action="sso.subgroups_synced",
        target_type="user",
        target_id=user_id,
        extra_data={
            "added": [str(s) for s in added],
            "removed": [str(s) for s in removed],
            "changed": [str(s) for s in changed],
            "provider_id": str(provider_id) if provider_id else None,
        },
    )
