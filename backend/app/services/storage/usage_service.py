"""
@file usage_service.py
@brief Per-user storage usage reporting.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.user import User
from app.repositories.media_repo import MediaRepository
from app.repositories.user_repo import UserRepository
from app.schemas.media import StorageByType, StorageUsageResponse


class StorageUsageService:
    """@brief Builds the storage usage summary for a user."""

    def __init__(self, media_repo: MediaRepository, user_repo: UserRepository) -> None:
        self._media_repo = media_repo
        self._user_repo = user_repo

    @classmethod
    def from_session(cls, session: AsyncSession) -> StorageUsageService:
        """@brief Build the service with repositories bound to ``session``."""
        return cls(MediaRepository(session), UserRepository(session))

    async def get_usage(self, viewer: User, user_id: uuid.UUID) -> StorageUsageResponse:
        """
        @brief Return usage for ``user_id``; only the user themself may read it.
        @param viewer Authenticated caller.
        @param user_id Target user UUID.
        @return StorageUsageResponse.
        @raises NotFoundError if the user does not exist.
        @raises AuthorizationError if viewer is not the target.
        """
        target = await self._user_repo.get_by_id(user_id, viewer.community_id)
        if target is None:
            raise NotFoundError(_("User not found"))
        if viewer.id != target.id:
            raise AuthorizationError(_("Cannot view another user's storage"))
        by_type = await self._media_repo.get_user_storage_by_type(target.id, target.community_id)
        return StorageUsageResponse(
            used_bytes=target.storage_used,
            quota_bytes=target.storage_quota,
            by_type=StorageByType(**by_type),
        )
