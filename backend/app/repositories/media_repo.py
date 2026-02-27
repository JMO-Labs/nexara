"""
@file media_repo.py
@brief Repository for media upload metadata and storage accounting.

Extends :class:`BaseRepository` with media-specific queries for
upload tracking, status updates, and user storage totals.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Media
from app.models.post import PostMedia
from app.repositories.base import BaseRepository


class MediaRepository(BaseRepository[Media]):
    """
    @brief Async repository for :class:`Media` entities.

    Handles CRUD for media metadata. Storage files are managed
    by the service layer via the storage backend.
    """

    model = Media

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(
        self,
        uploader_id: uuid.UUID,
        filename: str,
        content_type: str,
        storage_key: str,
        size_bytes: int,
        community_id: uuid.UUID,
    ) -> Media:
        """
        @brief Create a new media record with status ``processing``.

        @param uploader_id UUID of the uploading user.
        @param filename Original filename.
        @param content_type MIME type.
        @param storage_key Backend storage path.
        @param size_bytes File size in bytes.
        @param community_id Community scope.
        @return The persisted Media instance.
        """
        media = Media(
            uploader_id=uploader_id,
            community_id=community_id,
            filename=filename,
            content_type=content_type,
            storage_key=storage_key,
            size_bytes=size_bytes,
            status="processing",
        )
        return await super().create(media)

    async def get(self, media_id: uuid.UUID) -> Media | None:
        """
        @brief Fetch a single media record by ID.

        @param media_id UUID of the media.
        @return The Media instance or None.
        """
        return await self.get_by_id(media_id)

    async def get_by_ids(self, media_ids: list[uuid.UUID]) -> list[Media]:
        """
        @brief Fetch multiple media records by ID.

        @param media_ids List of media UUIDs.
        @return List of Media instances (order not guaranteed).
        """
        if not media_ids:
            return []
        stmt = select(Media).where(Media.id.in_(media_ids))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        media_id: uuid.UUID,
        status: str,
        *,
        thumbnail_key: str | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> Media | None:
        """
        @brief Update media status and optional thumbnail/dimensions.

        @param media_id UUID of the media.
        @param status New status (processing, ready, error).
        @param thumbnail_key Storage key for thumbnail (optional).
        @param width Image width in pixels (optional).
        @param height Image height in pixels (optional).
        @return The updated Media or None if not found.
        """
        media = await self.get(media_id)
        if media is None:
            return None
        data: dict = {"status": status}
        if thumbnail_key is not None:
            data["thumbnail_key"] = thumbnail_key
        if width is not None:
            data["width"] = width
        if height is not None:
            data["height"] = height
        return await self.update(media, data)

    async def delete_media(self, media_id: uuid.UUID) -> bool:
        """
        @brief Delete a media record (marks for cleanup).

        Removes the DB row. The service layer is responsible for
        deleting storage files and decrementing user quota.

        @param media_id UUID of the media to delete.
        @return True if a row was deleted, False if not found.
        """
        media = await self.get(media_id)
        if media is None:
            return False
        await self._session.delete(media)
        await self._session.flush()
        return True

    async def get_user_storage_used(self, user_id: uuid.UUID) -> int:
        """
        @brief Sum size_bytes for all media uploaded by the user.

        @param user_id UUID of the user.
        @return Total bytes used by the user's media.
        """
        stmt = select(func.coalesce(func.sum(Media.size_bytes), 0)).where(
            Media.uploader_id == user_id
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def attach_to_post(
        self,
        post_id: uuid.UUID,
        media_ids: list[uuid.UUID],
    ) -> None:
        """
        @brief Link media to a post via the post_media junction table.

        @param post_id UUID of the post.
        @param media_ids List of media UUIDs (order preserved as position).
        """
        for position, media_id in enumerate(media_ids):
            link = PostMedia(post_id=post_id, media_id=media_id, position=position)
            self._session.add(link)
        await self._session.flush()
