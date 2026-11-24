"""
@file serving.py
@brief Media read paths (metadata, original, thumbnail) with the NSFW and
       time-capsule guards, and the per-media cache policy.

Split from media_service.py.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.models.user import User
from app.schemas.media import MediaResponse

if TYPE_CHECKING:
    from app.repositories.media_repo import MediaRepository
    from app.repositories.time_capsule_repo import TimeCapsuleRepository
    from app.services.storage.base import StorageBackend


class MediaServingMixin:
    """@brief Serving half of ``MediaService``; expects its repos and storage."""

    _repo: MediaRepository
    _storage: StorageBackend
    _capsule_repo: TimeCapsuleRepository | None
    _community_id: uuid.UUID

    async def get_metadata(
        self, media_id: uuid.UUID, viewer_id: uuid.UUID | None = None
    ) -> MediaResponse:
        """
        @brief Return media metadata by ID (NSFW: adults only).
        @raises NotFoundError If media does not exist or is NSFW for a non-adult.
        """
        if await self._repo.nsfw_hidden(viewer_id, media_id=media_id):
            raise NotFoundError(_("Media not found"))
        media = await self._repo.get(media_id)
        if media is None:
            raise NotFoundError(_("Media not found"))
        return MediaResponse.model_validate(media)

    async def _guard_sealed(self, media_id: uuid.UUID, viewer_id: uuid.UUID | None) -> None:
        """@brief 404 for NSFW media and a non-adult viewer, or for media in an
        unopened time capsule (author bypasses)."""
        if await self._repo.nsfw_hidden(viewer_id, media_id=media_id) or (
            self._capsule_repo
            and await self._capsule_repo.is_sealed_media(media_id, self._community_id, viewer_id)
        ):
            raise NotFoundError(_("Media not found"))

    async def get_file(
        self,
        media_id: uuid.UUID,
        user: User,
    ) -> tuple[bytes, str]:
        """@brief Original file for ``user`` (see ``get_file_public``)."""
        return await self.get_file_public(media_id, user.id)

    async def get_file_public(
        self, media_id: uuid.UUID, viewer_id: uuid.UUID | None = None
    ) -> tuple[bytes, str]:
        """
        @brief Retrieve the original file content without auth.
        @param media_id UUID of the media.
        @return Tuple of (content bytes, content_type).
        @raises NotFoundError If media does not exist, is sealed in a capsule, or is
                NSFW and the viewer is not an adult.
        """
        await self._guard_sealed(media_id, viewer_id)
        media = await self._repo.get(media_id)
        if media is None:
            raise NotFoundError(_("Media not found"))
        data = await self._storage.get(media.storage_key)
        return data, media.content_type

    async def get_thumbnail(
        self, media_id: uuid.UUID, viewer_id: uuid.UUID | None = None
    ) -> tuple[bytes, str]:
        """
        @brief Retrieve the thumbnail content and content type.
        @param media_id UUID of the media.
        @return Tuple of (content bytes, content_type).
        @raises NotFoundError If media or thumbnail does not exist, or is sealed.
        """
        await self._guard_sealed(media_id, viewer_id)
        media = await self._repo.get(media_id)
        if media is None:
            raise NotFoundError(_("Media not found"))
        if not media.thumbnail_key:
            raise NotFoundError(_("Thumbnail not available"))
        data = await self._storage.get(media.thumbnail_key)
        return data, "image/webp"

    async def is_nsfw(self, media_id: uuid.UUID) -> bool:
        """@brief NSFW by own flag or via an NSFW post or album (no viewer check)."""
        return media_id in await self._repo.nsfw_media_among({media_id})
