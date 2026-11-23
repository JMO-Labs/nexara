"""
@file test_validation_audio.py
@brief Audio magic bytes, 25 MB cap (413 via the upload service) and routing.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppError
from app.services.media.audio import audio_base_type, check_audio_upload
from app.services.media_service import MediaService
from app.services.storage.validation import (
    UploadValidationError,
    validate_file_content,
    validate_file_size,
)

PAD = b"\x00" * 8


@pytest.mark.parametrize(
    ("header", "declared", "expected"),
    [
        (b"ID3\x04" + PAD, None, "audio/mpeg"),
        (b"\xff\xfb\x90\x00" + PAD, None, "audio/mpeg"),
        (b"\xff\xf3\x90\x00" + PAD, None, "audio/mpeg"),
        (b"\x00\x00\x00\x20ftypM4A " + PAD, None, "audio/mp4"),
        (b"\x00\x00\x00\x20ftypM4B " + PAD, None, "audio/mp4"),
        (b"\x00\x00\x00\x20ftypiso5" + PAD, "audio/mp4", "audio/mp4"),
        (b"\x00\x00\x00\x20ftypisom" + PAD, None, "video/mp4"),
        (b"OggS\x00\x02" + PAD, None, "audio/ogg"),
        (b"\x1a\x45\xdf\xa3" + PAD, "audio/webm", "audio/webm"),
        (b"\x1a\x45\xdf\xa3" + PAD, "video/webm", "video/webm"),
        (b"\xff\xd8\xff\xe0" + PAD, None, "image/jpeg"),
    ],
)
def test_magic_bytes(header, declared, expected):
    assert validate_file_content(header, declared) == expected


def test_audio_size_cap_is_25mb():
    validate_file_size(25 * 1024 * 1024, "audio/mpeg")
    with pytest.raises(UploadValidationError):
        validate_file_size(25 * 1024 * 1024 + 1, "audio/mpeg")


def test_base_type_strips_codecs_and_rejects_others():
    assert audio_base_type("audio/webm;codecs=opus") == "audio/webm"
    assert audio_base_type("image/png") is None


def test_check_rejects_wrong_bytes_and_oversize_413():
    with pytest.raises(AppError) as bad:
        check_audio_upload(b"\x89PNG\r\n\x1a\n" + PAD, "audio/mpeg", 16)
    assert bad.value.status_code == 400
    big = 26 * 1024 * 1024
    with pytest.raises(AppError) as over:
        check_audio_upload(b"ID3\x04" + b"\x00" * (big - 4), "audio/mpeg", big)
    assert over.value.status_code == 413


async def test_upload_routes_audio_to_transcode_not_thumbnail():
    repo = AsyncMock()
    repo.create.return_value = MagicMock(
        id=uuid.uuid4(), content_type="audio/mp4", uploader_id=uuid.uuid4(), filename="a",
        size_bytes=16, storage_key="k", thumbnail_key=None, status="processing",
        community_id=uuid.uuid4(), width=None, height=None, duration_secs=None,
        alt_text=None, created_at=__import__("datetime").datetime.now(),
    )  # fmt: skip
    svc = MediaService(repo, AsyncMock(), AsyncMock(), uuid.uuid4())
    user = MagicMock(id=uuid.uuid4())
    data = b"\x00\x00\x00\x20ftypM4A " + PAD
    with (
        patch("app.services.media_service.check_quota", AsyncMock()),
        patch("app.services.media_service.increment_storage_used", AsyncMock()),
        patch("app.services.media_service.invalidate_search_cache_for_community", AsyncMock()),
        patch("app.services.media_service.transcode_audio") as tc,
        patch("app.services.media_service.generate_thumbnail") as thumb,
    ):
        await svc.upload(user, data, "a.m4a", "audio/mp4", len(data))
    tc.delay.assert_called_once()
    thumb.delay.assert_not_called()
    assert repo.create.await_args.kwargs["content_type"] == "audio/mp4"
