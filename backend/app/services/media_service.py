"""
@file media_service.py
@brief Business logic for media upload, serving, and post attachment.

Validates file types and sizes, enforces user quotas, and coordinates
storage and database operations.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_search_cache_for_community
from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError
from app.core.i18n import _
from app.models.user import User
from app.repositories.activity_repo import ActivityRepository
from app.repositories.media_repo import MediaRepository
from app.repositories.user_repo import UserRepository
from app.schemas.media import MediaResponse
from app.services.activity_publish import record_activity
from app.services.media.multipart import (
    complete_multipart_upload as _complete_multipart_upload_impl,
)
from app.services.media.multipart import (
    init_multipart_upload as _init_multipart_upload_impl,
)
from app.services.media.multipart import (
    upload_part as _upload_part_impl,
)
from app.services.storage.base import StorageBackend
from app.services.storage.quota import (
    QuotaExceededError,
    check_quota,
    decrement_storage_used,
    increment_storage_used,
)
from app.tasks.ai_tasks import ocr_process_image
from app.tasks.media_tasks import generate_thumbnail

logger = structlog.get_logger(__name__)

MAX_IMAGE_SIZE = 20 * 1024 * 1024
"""@brief Maximum upload size in bytes (20 MB)."""

MAX_POST_MEDIA = 10
"""@brief Maximum number of media items attachable to one post."""

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
"""@brief MIME types accepted for image uploads."""


def enqueue_ocr(media_id: uuid.UUID, community_id: uuid.UUID, content_type: str) -> None:
    """
    @brief Enqueue OCR for ready images when an AI provider is configured.
    @param media_id Media UUID.
    @param community_id Tenant UUID.
    @param content_type MIME type of the upload.
    """
    if not content_type.startswith("image/") or not get_settings().AI_PROVIDER:
        return
    try:
        ocr_process_image.apply_async(
            args=[str(media_id), str(community_id)], queue="media", time_limit=3600
        )
    except Exception:  # OCR is an enhancement; never fail the upload
        logger.warning("ocr_enqueue_failed", media_id=str(media_id))


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
        *,
        valkey_client: Redis | None = None,
        activity_repo: ActivityRepository | None = None,
    ) -> None:
        self._repo = media_repo
        self._storage = storage_backend
        self._user_repo = user_repo
        self._community_id = community_id
        self._valkey = valkey_client
        self._activity_repo = activity_repo

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

        if self._activity_repo is not None:
            await record_activity(
                self._activity_repo,
                self._session(),
                None,
                community_id=self._community_id,
                actor_id=user.id,
                verb="media.uploaded",
                object_type="media",
                object_id=media.id,
                subgroup_id=None,
                visibility="private",
                metadata={
                    "actor_name": user.display_name,
                    "object_title": filename,
                },
            )

        generate_thumbnail.delay(str(media.id))
        await invalidate_search_cache_for_community(
            self._community_id, service="media", action="create", user_id=user.id
        )
        enqueue_ocr(media.id, self._community_id, media.content_type)

        return MediaResponse.model_validate(media)

    async def get_metadata(self, media_id: uuid.UUID) -> MediaResponse:
        """
        @brief Return media metadata by ID.

        @param media_id UUID of the media.
        @return MediaResponse with metadata.
        @raises NotFoundError If media does not exist.
        """
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
        @brief Retrieve the original file content and content type (authenticated).

        @param media_id UUID of the media.
        @param user Requesting user (for access control).
        @return Tuple of (content bytes, content_type).
        @raises NotFoundError If media does not exist.
        """
        return await self.get_file_public(media_id)

    async def get_file_public(
        self,
        media_id: uuid.UUID,
    ) -> tuple[bytes, str]:
        """
        @brief Retrieve the original file content without auth.

        Used by img/video tags that cannot send Bearer tokens.
        Access control is enforced at the post/upload level.

        @param media_id UUID of the media.
        @return Tuple of (content bytes, content_type).
        @raises NotFoundError If media does not exist.
        """
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
        from app.core.exceptions import AuthorizationError

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
        await invalidate_search_cache_for_community(
            self._community_id, service="media", action="delete", user_id=user.id
        )
        if self._activity_repo is not None:
            await self._activity_repo.invalidate("media", media_id)

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
        from app.core.exceptions import AuthorizationError

        if len(media_ids) > MAX_POST_MEDIA:
            raise AppError(
                code="TOO_MANY_MEDIA",
                message=_("Maximum %(max)d media items per post.") % {"max": MAX_POST_MEDIA},
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

    def _get_valkey(self) -> Redis:
        """@brief Get Valkey client, creating from settings if not injected."""
        if self._valkey is not None:
            return self._valkey
        from app.core.config import get_settings
        from app.core.valkey import DB_CACHE, get_pool

        return get_pool(get_settings(), DB_CACHE)

    async def init_multipart_upload(
        self,
        user: User,
        filename: str,
        content_type: str,
        total_size: int,
    ) -> dict[str, Any]:
        """
        @brief Initialize a multipart upload session.

        Delegates to :mod:`app.services.media.multipart`.
        """
        return await _init_multipart_upload_impl(
            self._session(),
            self._storage,
            self._repo,
            self._community_id,
            self._get_valkey(),
            user,
            filename,
            content_type,
            total_size,
        )

    async def upload_part(
        self,
        upload_id: str,
        part_number: int,
        data: bytes,
    ) -> dict[str, Any]:
        """
        @brief Store a single part of a multipart upload.

        Delegates to :mod:`app.services.media.multipart`.
        """
        return await _upload_part_impl(
            self._storage,
            self._get_valkey(),
            upload_id,
            part_number,
            data,
        )

    async def complete_multipart_upload(
        self,
        upload_id: str,
        user: User,
    ) -> MediaResponse:
        """
        @brief Assemble parts, create Media record, enqueue transcode if video.

        Delegates to :mod:`app.services.media.multipart`.
        """
        return await _complete_multipart_upload_impl(
            self._session(),
            self._storage,
            self._repo,
            self._community_id,
            self._get_valkey(),
            user,
            upload_id,
        )
