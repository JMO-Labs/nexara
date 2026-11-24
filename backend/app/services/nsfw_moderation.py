"""
@file nsfw_moderation.py
@brief Moderator NSFW flag/unflag for posts, albums and photos.

Community admins: anything. Group owners/moderators (incl. inherited from a
parent group): posts and albums in their group. Album owners use this endpoint
Authors, uploaders and album owners acting on their own content always get owner
rules (no lock; cannot clear a moderator lock), even when they moderate the group.
A non-admin moderator must be an adult to clear a flag (they must be able to
see what they unflag). Lock levels: admin flag -> 'admin', group moderator ->
'moderator'; clearing needs the actor's level >= the stored level.
Every change is audited and busts the search cache.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_search_cache_for_community
from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.user import User
from app.repositories.moderation_repo import ModerationRepository
from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository
from app.services.nsfw_rules import LOCK_RANK, apply_owner_flag, require_owner_may_flag
from app.services.subgroups.helpers import effective_membership, is_admin

_MOD_ROLES = {"moderator", "owner"}
_OWNER_COL = {"posts": "author_id", "galleries": "owner_id", "media": "uploader_id"}


class NsfwModerationService:
    """@brief Flag/unflag content NSFW as a moderator (see file brief)."""

    def __init__(
        self,
        repo: ModerationRepository,
        audit_repo: Any,
        community_id: uuid.UUID,
        session: AsyncSession,
        invalidate: Callable[[uuid.UUID], Awaitable[Any]] = invalidate_search_cache_for_community,
    ) -> None:
        self._repo = repo
        self._audit = audit_repo
        self._cid = community_id
        self._session = session
        self._invalidate = invalidate

    async def _group_moderator(self, subgroup_id: uuid.UUID | None, user: User) -> bool:
        """@brief User is owner/moderator of the group (directly or via a parent)."""
        if subgroup_id is None:
            return False
        groups = SubgroupRepository(self._session)
        group = await groups.get_by_id(subgroup_id, community_id=self._cid)
        if group is None:
            return False
        m = await effective_membership(SubgroupMemberRepository(self._session), groups, group, user)
        return m is not None and m.role in _MOD_ROLES

    async def set_flag(self, kind: str, entity_id: uuid.UUID, actor: User, value: bool) -> None:
        """
        @param kind "posts", "galleries" or "media".
        @throws NotFoundError missing/out of community; AuthorizationError not allowed.
        """
        entity = await self._repo.get_flaggable(kind, entity_id, self._cid)
        if entity is None:
            raise NotFoundError(_("Content not found"))
        admin = is_admin(actor)
        if not admin and getattr(entity, _OWNER_COL[kind]) == actor.id:
            # Own content: owner rules even for a group moderator (no lock, and a
            # moderator/admin lock cannot be cleared).
            await require_owner_may_flag(self._repo, self._cid, actor.id, value)
            if apply_owner_flag(entity, value):
                await self._session.flush()
                await self._record(kind, entity_id, actor, value, lock_level=entity.nsfw_lock_level)
            return
        moderator = admin or (
            kind != "media" and await self._group_moderator(entity.subgroup_id, actor)
        )
        if not moderator:
            raise AuthorizationError(_("Only moderators can change the NSFW flag"))
        if not value and not admin and not await self._repo.viewer_adult(actor.id):
            raise AuthorizationError(_("Only adults can remove the NSFW flag"))
        mine = "admin" if admin else "moderator"
        current = entity.nsfw_lock_level
        if not value and LOCK_RANK[current] > LOCK_RANK[mine]:
            raise AuthorizationError(_("An admin marked this NSFW"))
        # Never downgrade a stronger lock when re-flagging.
        level = mine if LOCK_RANK[mine] >= LOCK_RANK[current] else current
        await self._repo.set_nsfw(kind, entity_id, self._cid, value, level)
        await self._record(kind, entity_id, actor, value, lock_level=level if value else None)

    async def _record(
        self,
        kind: str,
        entity_id: uuid.UUID,
        actor: User,
        value: bool,
        *,
        lock_level: str | None,
    ) -> None:
        await self._audit.append(
            actor_id=actor.id,
            action=f"{kind}.marked_nsfw" if value else f"{kind}.unmarked_nsfw",
            target_type=kind,
            target_id=entity_id,
            extra_data={"value": value, "lock_level": lock_level},
        )
        await self._invalidate(self._cid)
