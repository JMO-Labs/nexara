"""
@file pending_link.py
@brief Deferred first SSO link, created only after the local 2FA step passes.

When a provider is first linked to an existing local account that has a
factor, the link is NOT created at callback time. Its fields ride as the
signed ``oauth_link`` claim of the ``2fa_pending`` token, and the link is
created only when that token completes the second factor. An abandoned
step leaves no link.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_oauth_link import UserOAuthLink
from app.repositories.oauth_repo import UserOAuthLinkRepository
from app.repositories.subgroup_repo import SubgroupMemberRepository
from app.repositories.user_repo import UserRepository
from app.services.oauth.group_mapper import sync_subgroups
from app.services.oauth.profile_sync import audit_role_synced
from app.services.oauth.role_sync import audit_role_sync_skipped, can_change_role


async def create_link(
    session: AsyncSession, user_id: uuid.UUID, link: dict[str, Any] | None
) -> None:
    """
    @brief Persist a held link, then its deferred role and subgroup sync; idempotent.

    @param session Request session.
    @param user_id Account that passed 2FA.
    @param link provider_id, sub, email_from_provider, avatar_url, role,
                subgroups (subgroup_id -> role, present when the provider
                syncs subgroups); None = no-op.
    """
    if not link:
        return
    links = UserOAuthLinkRepository(session)
    provider_id = uuid.UUID(str(link["provider_id"]))
    if await links.find_by_provider_and_sub(provider_id, str(link["sub"])):
        return
    await links.create(
        UserOAuthLink(
            user_id=user_id,
            provider_id=provider_id,
            sub=str(link["sub"]),
            email_from_provider=link.get("email_from_provider"),
            avatar_url=link.get("avatar_url"),
        )
    )
    role, subgroups = link.get("role"), link.get("subgroups")
    if not role and not isinstance(subgroups, dict):
        return
    users = UserRepository(session)
    user = await users.get_by_id(user_id)
    if user is None:
        return
    if role and user.role != role:
        old, new = user.role, str(role)
        if await can_change_role(users, user.community_id, user, new):
            await users.update(user, {"role": new})
            await audit_role_synced(session, user_id, old, new, provider_id=provider_id)
        else:
            await audit_role_sync_skipped(session, user_id, old, new, provider_id)
    if isinstance(subgroups, dict):
        mapped = {uuid.UUID(str(k)): str(v) for k, v in subgroups.items()}
        await sync_subgroups(
            SubgroupMemberRepository(session),
            user.community_id,
            user_id,
            mapped,
            session=session,
            provider_id=provider_id,
        )
