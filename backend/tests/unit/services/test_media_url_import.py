"""
@file test_media_url_import.py
@brief Image import from URL: sniffing, size cap, guard errors, upload hand-off.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppError
from app.core.http_safe import UnsafeUrlError
from app.services.media.url_import import MAX_IMPORT_BYTES, import_image_from_url, sniff_image

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 16
MOD = "app.services.media.url_import.safe_fetch"


def test_sniff_image():
    assert sniff_image(PNG) == ("image/png", "png")
    assert sniff_image(WEBP) == ("image/webp", "webp")
    assert sniff_image(b"\xff\xd8\xff\xe0rest") == ("image/jpeg", "jpg")
    assert sniff_image(b"<html>") is None


async def test_imports_png_via_upload():
    svc = MagicMock()
    svc.upload = AsyncMock(return_value="media")
    with patch(MOD, AsyncMock(return_value=PNG)):
        out = await import_image_from_url(svc, MagicMock(), "https://x.test/pics/cabin.photo?x=1")
    assert out == "media"
    kw = svc.upload.await_args.kwargs
    assert kw["content_type"] == "image/png"
    assert kw["filename"] == "cabin.png"
    assert kw["size"] == len(PNG)


@pytest.mark.parametrize(
    ("fetch", "code"),
    [
        (AsyncMock(side_effect=UnsafeUrlError("private")), "INVALID_URL"),
        (AsyncMock(side_effect=TimeoutError()), "FETCH_FAILED"),
        (AsyncMock(return_value=b"<html>nope</html>"), "INVALID_FILE_TYPE"),
        (AsyncMock(return_value=PNG + b"\x00" * MAX_IMPORT_BYTES), "FILE_TOO_LARGE"),
    ],
)
async def test_rejections(fetch, code):
    svc = MagicMock()
    svc.upload = AsyncMock()
    with patch(MOD, fetch), pytest.raises(AppError) as err:
        await import_image_from_url(svc, MagicMock(), "https://x.test/a.png")
    assert err.value.code == code
    svc.upload.assert_not_awaited()
