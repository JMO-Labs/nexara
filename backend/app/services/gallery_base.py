"""
@file gallery_base.py
@brief Shared state and visibility helpers for the gallery service mixins.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gallery import Gallery
from app.models.subgroup import SubgroupMember
from app.repositories.activity_repo import ActivityRepository
from app.repositories.gallery_repo import GalleryRepository


class GalleryServiceBase:
    """@brief Constructor and permission helpers shared by gallery service parts."""
    """@brief Service layer for galleries."""

    def __init__(
        self,
        gallery_repo: GalleryRepository,
        community_id: uuid.UUID,
        session: AsyncSession,
        *,
        notification_service: Any | None = None,
        audit_repo: Any | None = None,
        activity_repo: ActivityRepository | None = None,
    ) -> None:
        self._repo = gallery_repo
        self._community_id = community_id
        self._session = session
        self._notifications = notification_service
        self._audit_repo = audit_repo
        self._activity_repo = activity_repo

    # ── Helpers ───────────────────────────────────────────────────────

    async def _user_subgroup_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """Direct memberships expanded with descendants (parent → child cascade)."""
        from app.repositories.subgroup_repo import expand_with_descendants

        stmt = select(SubgroupMember.subgroup_id).where(SubgroupMember.user_id == user_id)
        result = await self._session.execute(stmt)
        direct = list(result.scalars().all())
        return await expand_with_descendants(self._session, direct)

    async def _can_view(self, gallery: Gallery, user_id: uuid.UUID) -> bool:
        if gallery.visibility == "community":
            return True
        if gallery.visibility == "private":
            if gallery.owner_id == user_id:
                return True
            return await self._repo.is_collaborator(gallery.id, user_id)
        if gallery.visibility == "subgroup":
            if gallery.subgroup_id is None:
                return False
            ids = await self._user_subgroup_ids(user_id)
            return gallery.subgroup_id in ids
        return False

    async def _can_contribute(self, gallery: Gallery, user_id: uuid.UUID) -> bool:
        if gallery.owner_id == user_id:
            return True
        policy = gallery.contribution_policy
        if policy == "owner_only":
            return False
        if policy == "collaborators":
            return await self._repo.is_collaborator(gallery.id, user_id)
        if policy == "community":
            return await self._can_view(gallery, user_id)
        return False
