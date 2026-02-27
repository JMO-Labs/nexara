"""
@file test_media_service.py
@brief Unit tests for MediaService.

Tests upload validation, quota enforcement, delete, and attach_to_post
using mocked dependencies (AsyncMock for repos/storage).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.services.storage.quota import QuotaExceededError

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()
OTHER_USER_ID = uuid.uuid4()


def _make_user(storage_used: int = 0, storage_quota: int = 10 * 1024 * 1024) -> MagicMock:
    """@brief Create a mock User with storage fields."""
    user = MagicMock()
    user.id = USER_ID
    user.storage_used = storage_used
    user.storage_quota = storage_quota
    return user


def _make_media(
    uploader_id: uuid.UUID = USER_ID,
    status: str = "ready",
    size_bytes: int = 1000,
) -> MagicMock:
    """@brief Create a mock Media record."""
    media = MagicMock()
    media.id = uuid.uuid4()
    media.uploader_id = uploader_id
    media.status = status
    media.size_bytes = size_bytes
    media.storage_key = "originals/test.jpg"
    media.thumbnail_key = "thumbnails/test.webp"
    media.filename = "test.jpg"
    media.content_type = "image/jpeg"
    media.alt_text = None
    media.width = 800
    media.height = 600
    media.created_at = datetime.now(timezone.utc)
    return media


class TestUpload:
    """@brief Tests for MediaService.upload()."""

    @pytest.mark.asyncio
    async def test_upload_stores_file_and_creates_db_record(self):
        """upload should store file via storage backend and create Media record."""
        from app.services.media_service import MediaService

        mock_repo = AsyncMock()
        mock_repo._session = AsyncMock()
        mock_storage = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_media = _make_media(status="processing")
        mock_media.storage_key = "originals/abc-123.jpg"
        mock_repo.create.return_value = mock_media

        with patch("app.services.media_service.check_quota", new_callable=AsyncMock), \
             patch("app.services.media_service.increment_storage_used", new_callable=AsyncMock), \
             patch("app.services.media_service.generate_thumbnail"):
            service = MediaService(
                media_repo=mock_repo,
                storage_backend=mock_storage,
                user_repo=mock_user_repo,
                community_id=COMMUNITY_ID,
            )
            user = _make_user()
            file_data = b"fake image data"
            result = await service.upload(
                user=user,
                file_data=file_data,
                filename="photo.jpg",
                content_type="image/jpeg",
                size=len(file_data),
            )

        mock_storage.put.assert_awaited_once()
        mock_repo.create.assert_awaited_once()
        assert result.status == "processing"

    @pytest.mark.asyncio
    async def test_upload_rejects_file_exceeding_size_limit(self):
        """upload should reject files larger than 20 MB."""
        from app.services.media_service import MediaService

        mock_repo = AsyncMock()
        mock_storage = AsyncMock()
        mock_user_repo = AsyncMock()
        service = MediaService(
            media_repo=mock_repo,
            storage_backend=mock_storage,
            user_repo=mock_user_repo,
            community_id=COMMUNITY_ID,
        )

        user = _make_user()
        oversized = 21 * 1024 * 1024

        with pytest.raises(AppError) as exc_info:
            await service.upload(
                user=user,
                file_data=b"x" * 100,
                filename="huge.jpg",
                content_type="image/jpeg",
                size=oversized,
            )

        assert exc_info.value.status_code == 400
        assert "FILE_TOO_LARGE" in exc_info.value.code or "20" in exc_info.value.message
        mock_storage.put.assert_not_awaited()
        mock_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_upload_rejects_file_exceeding_user_quota(self):
        """upload should reject when storage_used + size would exceed quota."""
        from app.services.media_service import MediaService

        mock_repo = AsyncMock()
        mock_repo._session = AsyncMock()
        mock_storage = AsyncMock()
        mock_user_repo = AsyncMock()

        async def check_quota_raises(session, user_id, size):
            raise QuotaExceededError(quota=1000, used=900, upload_size=200)

        with patch(
            "app.services.media_service.check_quota",
            side_effect=check_quota_raises,
        ):
            service = MediaService(
                media_repo=mock_repo,
                storage_backend=mock_storage,
                user_repo=mock_user_repo,
                community_id=COMMUNITY_ID,
            )
            user = _make_user(storage_used=900, storage_quota=1000)

            with pytest.raises(AppError) as exc_info:
                await service.upload(
                    user=user,
                    file_data=b"x" * 200,
                    filename="photo.jpg",
                    content_type="image/jpeg",
                    size=200,
                )

        assert exc_info.value.status_code == 413
        mock_storage.put.assert_not_awaited()
        mock_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_upload_rejects_invalid_file_type(self):
        """upload should reject non-image content types."""
        from app.services.media_service import MediaService

        mock_repo = AsyncMock()
        mock_storage = AsyncMock()
        mock_user_repo = AsyncMock()
        service = MediaService(
            media_repo=mock_repo,
            storage_backend=mock_storage,
            user_repo=mock_user_repo,
            community_id=COMMUNITY_ID,
        )

        user = _make_user()

        with pytest.raises(AppError) as exc_info:
            await service.upload(
                user=user,
                file_data=b"content",
                filename="doc.pdf",
                content_type="application/pdf",
                size=7,
            )

        assert exc_info.value.status_code == 400
        mock_storage.put.assert_not_awaited()
        mock_repo.create.assert_not_awaited()


class TestGetMetadata:
    """@brief Tests for MediaService.get_metadata()."""

    @pytest.mark.asyncio
    async def test_get_metadata_returns_response_for_existing_media(self):
        """get_metadata should return MediaResponse when media exists."""
        from app.services.media_service import MediaService

        mock_media = _make_media()
        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_media
        mock_storage = AsyncMock()
        mock_user_repo = AsyncMock()

        with patch("app.services.media_service.MediaResponse") as MockResponse:
            MockResponse.model_validate.return_value = MagicMock()
            service = MediaService(
                media_repo=mock_repo,
                storage_backend=mock_storage,
                user_repo=mock_user_repo,
                community_id=COMMUNITY_ID,
            )

            result = await service.get_metadata(mock_media.id)

        mock_repo.get.assert_awaited_once_with(mock_media.id)
        MockResponse.model_validate.assert_called_once_with(mock_media)
        assert result is not None


class TestDelete:
    """@brief Tests for MediaService.delete()."""

    @pytest.mark.asyncio
    async def test_delete_decrements_user_storage_used(self):
        """delete should decrement user storage_used and delete storage files."""
        from app.services.media_service import MediaService

        mock_repo = AsyncMock()
        mock_repo._session = AsyncMock()
        mock_repo.get.return_value = _make_media(size_bytes=5000)
        mock_repo.delete_media.return_value = True
        mock_storage = AsyncMock()
        mock_user_repo = AsyncMock()

        async def decrement_side_effect(session, user_id, size):
            assert user_id == USER_ID
            assert size == 5000

        with patch(
            "app.services.media_service.decrement_storage_used",
            side_effect=decrement_side_effect,
        ):
            service = MediaService(
                media_repo=mock_repo,
                storage_backend=mock_storage,
                user_repo=mock_user_repo,
                community_id=COMMUNITY_ID,
            )
            user = _make_user()

            await service.delete(mock_repo.get.return_value.id, user)

        mock_storage.delete.assert_awaited()
        mock_repo.delete_media.assert_awaited_once()


class TestAttachToPost:
    """@brief Tests for MediaService.attach_to_post()."""

    @pytest.mark.asyncio
    async def test_attach_to_post_rejects_media_not_owned_by_user(self):
        """attach_to_post should reject media not owned by the user."""
        from app.services.media_service import MediaService

        mock_repo = AsyncMock()
        mock_repo.get_by_ids.return_value = [_make_media(uploader_id=OTHER_USER_ID)]
        mock_storage = AsyncMock()
        mock_user_repo = AsyncMock()
        service = MediaService(
            media_repo=mock_repo,
            storage_backend=mock_storage,
            user_repo=mock_user_repo,
            community_id=COMMUNITY_ID,
        )
        user = _make_user()
        post_id = uuid.uuid4()
        media_ids = [mock_repo.get_by_ids.return_value[0].id]

        with pytest.raises(AuthorizationError):
            await service.attach_to_post(post_id, media_ids, user)

        mock_repo.attach_to_post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_attach_to_post_rejects_media_with_status_not_ready(self):
        """attach_to_post should reject media with status != ready."""
        from app.services.media_service import MediaService

        mock_repo = AsyncMock()
        mock_repo.get_by_ids.return_value = [_make_media(status="processing")]
        mock_storage = AsyncMock()
        mock_user_repo = AsyncMock()
        service = MediaService(
            media_repo=mock_repo,
            storage_backend=mock_storage,
            user_repo=mock_user_repo,
            community_id=COMMUNITY_ID,
        )
        user = _make_user()
        post_id = uuid.uuid4()
        media_ids = [mock_repo.get_by_ids.return_value[0].id]

        with pytest.raises(AppError) as exc_info:
            await service.attach_to_post(post_id, media_ids, user)

        assert exc_info.value.status_code == 400
        mock_repo.attach_to_post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_attach_to_post_rejects_more_than_10_media_ids(self):
        """attach_to_post should reject more than 10 media IDs."""
        from app.services.media_service import MediaService

        mock_repo = AsyncMock()
        mock_storage = AsyncMock()
        mock_user_repo = AsyncMock()
        service = MediaService(
            media_repo=mock_repo,
            storage_backend=mock_storage,
            user_repo=mock_user_repo,
            community_id=COMMUNITY_ID,
        )
        user = _make_user()
        post_id = uuid.uuid4()
        media_ids = [uuid.uuid4() for _ in range(11)]

        with pytest.raises(AppError) as exc_info:
            await service.attach_to_post(post_id, media_ids, user)

        assert exc_info.value.status_code == 400
        mock_repo.get_by_ids.assert_not_awaited()
        mock_repo.attach_to_post.assert_not_awaited()
