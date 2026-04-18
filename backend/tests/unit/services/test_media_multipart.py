"""
@file test_media_multipart.py
@brief Unit tests for multipart upload in MediaService.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppError
from app.services.media_service import MediaService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()


def _make_user(user_id=USER_ID):
    user = MagicMock()
    user.id = user_id
    user.storage_used_bytes = 0
    user.storage_quota_bytes = 1024 * 1024 * 1024  # 1GB
    return user


def _make_service():
    mock_valkey = AsyncMock()
    mock_valkey.setex = AsyncMock()
    mock_valkey.get = AsyncMock(return_value=None)
    mock_valkey.delete = AsyncMock()
    return MediaService(
        media_repo=AsyncMock(),
        storage_backend=MagicMock(),
        user_repo=AsyncMock(),
        community_id=COMMUNITY_ID,
        valkey_client=mock_valkey,
    )


class TestInitMultipartUpload:
    @pytest.mark.asyncio
    async def test_creates_upload_session(self):
        service = _make_service()
        user = _make_user()

        with patch("app.services.media.multipart.check_quota", new_callable=AsyncMock):
            result = await service.init_multipart_upload(
                user, "video.mp4", "video/mp4", 50 * 1024 * 1024
            )

        assert "upload_id" in result
        assert "part_size" in result
        assert result["part_size"] > 0

    @pytest.mark.asyncio
    async def test_rejects_invalid_content_type(self):
        service = _make_service()
        user = _make_user()

        with pytest.raises(AppError, match="type|unsupported"):
            await service.init_multipart_upload(user, "file.exe", "application/octet-stream", 1024)

    @pytest.mark.asyncio
    async def test_rejects_oversized_upload(self):
        service = _make_service()
        user = _make_user()

        with pytest.raises(AppError, match="size|large|exceed"):
            await service.init_multipart_upload(user, "huge.mp4", "video/mp4", 600 * 1024 * 1024)
