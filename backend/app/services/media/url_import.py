"""
@file url_import.py
@brief Import an image from a public URL into media storage (cover/banner
       "paste a link"). Fetched server-side through the SSRF guard so viewers
       never hotlink third-party hosts; type is sniffed from the bytes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

from app.core.exceptions import AppError
from app.core.http_safe import UnsafeUrlError, safe_fetch
from app.core.i18n import _
from app.models.user import User
from app.schemas.media import MediaResponse

if TYPE_CHECKING:
    from app.services.media_service import MediaService

MAX_IMPORT_BYTES = 20 * 1024 * 1024

_MAGIC: tuple[tuple[bytes, str, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"GIF87a", "image/gif", "gif"),
    (b"GIF89a", "image/gif", "gif"),
)


def sniff_image(data: bytes) -> tuple[str, str] | None:
    """
    @brief Detect JPEG/PNG/GIF/WebP from magic bytes.
    @return (content_type, extension) or None.
    """
    for magic, ctype, ext in _MAGIC:
        if data.startswith(magic):
            return ctype, ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None


async def import_image_from_url(service: MediaService, user: User, url: str) -> MediaResponse:
    """
    @brief Download ``url`` and store it as the user's media.
    @raises AppError INVALID_URL / FETCH_FAILED / FILE_TOO_LARGE / INVALID_FILE_TYPE
    """
    try:
        data = await safe_fetch(url, timeout=15.0, max_bytes=MAX_IMPORT_BYTES + 1)
    except UnsafeUrlError as exc:
        raise AppError(
            code="INVALID_URL", message=_("That link can't be used"), status_code=400
        ) from exc
    except Exception as exc:  # network errors, timeouts
        raise AppError(
            code="FETCH_FAILED", message=_("Couldn't download that image"), status_code=400
        ) from exc
    if len(data) > MAX_IMPORT_BYTES:
        raise AppError(
            code="FILE_TOO_LARGE", message=_("Image is larger than 20 MB"), status_code=400
        )
    kind = sniff_image(data)
    if kind is None:
        raise AppError(
            code="INVALID_FILE_TYPE",
            message=_("That link isn't a JPEG, PNG, GIF or WebP image"),
            status_code=400,
        )
    ctype, ext = kind
    stem = (urlparse(url).path.rsplit("/", 1)[-1].rsplit(".", 1)[0] or "image")[:60]
    return await service.upload(
        user=user, file_data=data, filename=f"{stem}.{ext}", content_type=ctype, size=len(data)
    )
