"""
@file media_service.py
@brief Business logic for media upload, serving, and post attachment.

Validates file types and sizes, enforces user quotas, and coordinates
storage and database operations.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.i18n import _
from app.models.user import User
from app.repositories.media_repo import MediaRepository
from app.repositories.user_repo import UserRepository
from app.schemas.media import MediaResponse
from app.services.storage.base import StorageBackend, StorageKeyNotFoundError
from app.services.storage.quota import (
    QuotaExceededError,
    check_quota,
    decrement_storage_used,
    increment_storage_used,
)
from app.tasks.media_tasks import generate_thumbnail

logger = structlog.get_logger(__name__)

MAX_IMAGE_SIZE = 20 * 1024 * 1024
"""@brief Maximum upload size in bytes (20 MB)."""

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
"""@brief MIME types accepted for image uploads."""


class MediaService:
    """
    @brief Service layer for media upload, retrieval, and attachment.

    @param media_repo MediaRepository instance.
    @param storage_backend Storage backend for file I/O.
    @param user_repo UserRepository for quota updates.
    @param community_id UUID of the community scope.
    """

    def __init__(
        self,
        media_repo: MediaRepository,
        storage_backend: StorageBackend,
        user_repo: UserRepository,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = media_repo
        self._storage = storage_backend
        self._user_repo = user_repo
        self._community_id = community_id

    def _session(self) -> AsyncSession:
        """@brief Get the session from the media repo for quota operations."""
        return self._repo._session

    async def upload(
        self,
        user: User,
        file_data: bytes,
        filename: str,
        content_type: str,
        size: int,
    ) -> MediaResponse:
        """
        @brief Upload an image, store it, create a media record, and enqueue thumbnail.

        @param user The uploading user.
        @param file_data Raw file bytes.
        @param filename Original filename.
        @param content_type MIME type.
        @param size File size in bytes.
        @return MediaResponse for the created media.
        @raises ValueError If content type or size is invalid.
        @raises QuotaExceededError If upload would exceed user quota.
        """
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise AppError(
                code="INVALID_FILE_TYPE",
                message=_("Invalid file type. Only JPEG, PNG, GIF, and WebP are allowed."),
                status_code=400,
            )
        if size > MAX_IMAGE_SIZE:
            raise AppError(
                code="FILE_TOO_LARGE",
                message=_("File size exceeds 20 MB limit."),
                status_code=400,
            )
        if len(file_data) != size:
            raise AppError(
                code="FILE_SIZE_MISMATCH",
                message=_("File size mismatch."),
                status_code=400,
            )

        try:
            await check_quota(self._session(), user.id, size)
        except QuotaExceededError as exc:
            raise AppError(
                code="QUOTA_EXCEEDED",
                message=_("Storage quota exceeded. Please free up space."),
                status_code=413,
                details={"quota": exc.quota, "used": exc.used, "upload_size": exc.upload_size},
            ) from exc

        ext = "jpg" if content_type == "image/jpeg" else content_type.split("/")[-1]
        storage_key = f"originals/{uuid.uuid4()}.{ext}"

        await self._storage.put(storage_key, file_data, content_type)

        media = await self._repo.create(
            uploader_id=user.id,
            filename=filename,
            content_type=content_type,
            storage_key=storage_key,
            size_bytes=size,
            community_id=self._community_id,
        )
        await increment_storage_used(self._session(), user.id, size)

        generate_thumbnail.delay(str(media.id))

        return MediaResponse.model_validate(media)

    async def get_metadata(self, media_id: uuid.UUID) -> MediaResponse:
        """
        @brief Return media metadata by ID.

        @param media_id UUID of the media.
        @return MediaResponse with metadata.
        @raises NotFoundError If media does not exist.
        """
        from app.core.exceptions import NotFoundError

        media = await self._repo.get(media_id)
        if media is None:
            raise NotFoundError(_("Media not found"))
        return MediaResponse.model_validate(media)

    async def get_file(
        self,
        media_id: uuid.UUID,
        user: User,
    ) -> tuple[bytes, str]:
        """
        @brief Retrieve the original file content and content type.

        @param media_id UUID of the media.
        @param user Requesting user (for access control).
        @return Tuple of (content bytes, content_type).
        @raises NotFoundError If media does not exist.
        @raises StorageKeyNotFoundError If file is missing in storage.
        """
        from app.core.exceptions import NotFoundError

        media = await self._repo.get(media_id)
        if media is None:
            raise NotFoundError(_("Media not found"))
        data = await self._storage.get(media.storage_key)
        return data, media.content_type

    async def get_thumbnail(self, media_id: uuid.UUID) -> tuple[bytes, str]:
        """
        @brief Retrieve the thumbnail content and content type.

        @param media_id UUID of the media.
        @return Tuple of (content bytes, content_type).
        @raises NotFoundError If media or thumbnail does not exist.
        """
        from app.core.exceptions import NotFoundError

        media = await self._repo.get(media_id)
        if media is None:
            raise NotFoundError(_("Media not found"))
        if not media.thumbnail_key:
            raise NotFoundError(_("Thumbnail not available"))
        data = await self._storage.get(media.thumbnail_key)
        return data, "image/webp"

    async def delete(self, media_id: uuid.UUID, user: User) -> None:
        """
        @brief Delete media and decrement user quota.

        @param media_id UUID of the media.
        @param user Requesting user (must be owner).
        @raises NotFoundError If media does not exist.
        @raises AuthorizationError If user is not the owner.
        """
        from app.core.exceptions import AuthorizationError, NotFoundError

        media = await self._repo.get(media_id)
        if media is None:
            raise NotFoundError(_("Media not found"))
        if media.uploader_id != user.id:
            raise AuthorizationError(_("You do not own this media"))

        await self._storage.delete(media.storage_key)
        if media.thumbnail_key:
            await self._storage.delete(media.thumbnail_key)
        await decrement_storage_used(self._session(), user.id, media.size_bytes)
        await self._repo.delete_media(media_id)

    async def attach_to_post(
        self,
        post_id: uuid.UUID,
        media_ids: list[uuid.UUID],
        user: User,
    ) -> None:
        """
        @brief Attach media to a post.

        @param post_id UUID of the post.
        @param media_ids List of media UUIDs (max 10).
        @param user Requesting user (must own all media).
        @raises ValueError If validation fails.
        """
        from app.core.exceptions import AuthorizationError, NotFoundError

        if len(media_ids) > 10:
            raise AppError(
                code="TOO_MANY_MEDIA",
                message=_("Maximum 10 media items per post."),
                status_code=400,
            )

        media_list = await self._repo.get_by_ids(media_ids)
        if len(media_list) != len(media_ids):
            raise NotFoundError(_("One or more media items not found"))

        for media in media_list:
            if media.uploader_id != user.id:
                raise AuthorizationError(_("You do not own one or more of these media items"))
            if media.status != "ready":
                raise AppError(
                    code="MEDIA_NOT_READY",
                    message=_("All media must have status 'ready' before attaching"),
                    status_code=400,
                )

        await self._repo.attach_to_post(post_id, media_ids)
