"""
@file test_multipart_upload_part.py
@brief Unit tests for media.multipart.upload_part (nexara#396).
"""

from __future__ import annotations

import hashlib
import json
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import NotFoundError
from app.services.media.multipart import upload_part


class TestUploadPart:
    async def test_missing_session_raises_not_found(self):
        valkey = AsyncMock()
        valkey.get.return_value = None
        storage = AsyncMock()

        with pytest.raises(NotFoundError):
            await upload_part(storage, valkey, "gone", 1, b"data")

        valkey.setex.assert_not_awaited()
        storage.put.assert_not_awaited()

    async def test_stores_part_and_returns_etag(self):
        valkey = AsyncMock()
        valkey.get.return_value = json.dumps({"parts": {}})
        storage = AsyncMock()

        result = await upload_part(storage, valkey, "up1", 2, b"abc")

        etag = hashlib.md5(b"abc", usedforsecurity=False).hexdigest()
        assert result == {"part_number": 2, "etag": etag}
        storage.put.assert_awaited_once_with(
            "multipart/up1/part_2", b"abc", "application/octet-stream"
        )
