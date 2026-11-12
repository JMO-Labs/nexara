"""
@file moderation_service.py
@brief Admin moderation actions: NSFW marking with audit log and cache invalidation.
"""

from __future__ import annotations

import uuid

from app.core.cache import invalidate_search_cache_for_community
from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.moderation_repo import ModerationRepository


class ModerationService:
    """
    @brief Marks content NSFW on behalf of an admin.

    @param repo         ModerationRepository.
    @param audit_repo   AuditRepository.
    @param community_id Community scope.
    """

    def __init__(
        self, repo: ModerationRepository, audit_repo: AuditRepository, community_id: uuid.UUID
    ) -> None:
        self._repo = repo
        self._audit = audit_repo
        self._community_id = community_id

    async def mark_nsfw(
        self, kind: str, target_id: uuid.UUID, admin: User, ip: str | None
    ) -> None:
        """
        @brief Set is_nsfw=true, audit-log and invalidate the search cache.

        @param kind      "post" or "media".
        @param target_id Target UUID.
        @param admin     Acting admin.
        @param ip        Request IP.
        @raises NotFoundError If the target does not exist.
        """
        if not await self._repo.set_nsfw(kind, target_id, self._community_id, True):
            raise NotFoundError(message=_("Content not found"))
        await self._audit.append(
            actor_id=admin.id,
            action=f"moderation.{kind}.marked_nsfw",
            target_type=kind,
            target_id=target_id,
            ip_address=ip,
        )
        await invalidate_search_cache_for_community(self._community_id)
