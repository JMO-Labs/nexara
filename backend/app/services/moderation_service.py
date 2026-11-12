"""
@file moderation_service.py
@brief Admin moderation actions (NSFW tagging) with audit logging.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.cache import invalidate_search_cache_for_community
from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.models.media import Media
from app.models.post import Post

_MODELS: dict[str, type] = {"posts": Post, "media": Media}


class ModerationService:
    """
    @brief Marks posts/media NSFW, writes an audit entry, busts the search cache.

    @param session Async DB session.
    @param audit_repo AuditRepository.
    @param community_id Community scope.
    @param invalidate Cache invalidation coroutine (injectable for tests).
    """

    def __init__(
        self,
        session: Any,
        audit_repo: Any,
        community_id: uuid.UUID,
        invalidate: Callable[[uuid.UUID], Awaitable[Any]] = invalidate_search_cache_for_community,
    ) -> None:
        self._session = session
        self._audit = audit_repo
        self._community_id = community_id
        self._invalidate = invalidate

    async def mark_nsfw(self, kind: str, entity_id: uuid.UUID, admin_id: uuid.UUID) -> None:
        """
        @brief Set is_nsfw=true on a post or media item.

        @param kind "posts" or "media".
        @param entity_id Target UUID.
        @param admin_id Acting admin.
        @throws NotFoundError if missing, deleted, or in another community.
        """
        entity = await self._session.get(_MODELS[kind], entity_id)
        if (
            entity is None
            or entity.community_id != self._community_id
            or getattr(entity, "deleted_at", None) is not None
        ):
            raise NotFoundError(_("Content not found"))
        entity.is_nsfw = True
        await self._session.flush()
        await self._audit.append(
            actor_id=admin_id,
            action=f"{kind}.marked_nsfw",
            target_type=kind,
            target_id=entity_id,
        )
        await self._invalidate(self._community_id)
