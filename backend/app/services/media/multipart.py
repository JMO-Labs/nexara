"""
@file multipart.py
@brief Multipart upload business logic for large files (video, etc.).

Validates type/size, manages Valkey session state, assembles parts, and
creates Media records. Orchestrated by :mod:`app.services.media_service`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.i18n import _
from app.core.transcode import ALLOWED_VIDEO_TYPES, MAX_VIDEO_SIZE
from app.models.user import User
from app.repositories.media_repo import MediaRepository
from app.schemas.media import MediaResponse
from app.services.storage.base import StorageBackend
from app.services.storage.quota import (
    QuotaExceededError,
    check_quota,
    increment_storage_used,
)
from app.tasks.media_tasks import generate_thumbnail, transcode_video

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
"""@brief MIME types accepted for image uploads."""

MULTIPART_ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES
"""@brief MIME types accepted for multipart uploads (images + videos)."""

MULTIPART_PART_SIZE = 5 * 1024 * 1024
"""@brief Part size in bytes (5 MB) for multipart uploads."""

MULTIPART_SESSION_TTL = 86400
"""@brief Session TTL in seconds (24 hours)."""


async def init_multipart_upload(
    session: AsyncSession,
    storage: StorageBackend,
    media_repo: MediaRepository,
    community_id: uuid.UUID,
    valkey: Redis,
    user: User,
    filename: str,
    content_type: str,
    total_size: int,
) -> dict[str, Any]:
    """
    @brief Initialize a multipart upload session.

    Validates type, size, and quota. Stores session in Valkey.
    Returns upload_id and part_size.

    @param session Async DB session for quota checks.
    @param storage Storage backend.
    @param media_repo Media repository (unused in init).
    @param community_id Community UUID.
    @param valkey Valkey client for session storage.
    @param user The uploading user.
    @param filename Original filename.
    @param content_type MIME type.
    @param total_size Total file size in bytes.
    @return Dict with upload_id and part_size.
    """
    if content_type not in MULTIPART_ALLOWED_TYPES:
        raise AppError(
            code="INVALID_FILE_TYPE",
            message=_("Unsupported file type for multipart upload."),
            status_code=400,
        )
    if total_size > MAX_VIDEO_SIZE:
        raise AppError(
            code="FILE_TOO_LARGE",
            message=_("File size exceeds 500 MB limit."),
            status_code=400,
        )

    try:
        await check_quota(session, user.id, total_size)
    except QuotaExceededError as exc:
        raise AppError(
            code="QUOTA_EXCEEDED",
            message=_("Storage quota exceeded. Please free up space."),
            status_code=413,
            details={"quota": exc.quota, "used": exc.used, "upload_size": exc.upload_size},
        ) from exc

    upload_id = str(uuid.uuid4())
    sess_data = {
        "user_id": str(user.id),
        "filename": filename,
        "content_type": content_type,
        "total_size": total_size,
        "parts": {},
    }
    await valkey.setex(
        f"multipart:{upload_id}",
        MULTIPART_SESSION_TTL,
        json.dumps(sess_data),
    )
    return {"upload_id": upload_id, "part_size": MULTIPART_PART_SIZE}


async def upload_part(
    storage: StorageBackend,
    valkey: Redis,
    upload_id: str,
    part_number: int,
    data: bytes,
) -> dict[str, Any]:
    """
    @brief Store a single part of a multipart upload.

    @param storage Storage backend.
    @param valkey Valkey client.
    @param upload_id Upload session ID.
    @param part_number 1-based part index.
    @param data Part bytes.
    @return Dict with part_number and etag.
    """
    raw = await valkey.get(f"multipart:{upload_id}")
    if raw is None:
        raise NotFoundError(_("Upload session not found or expired"))
    sess_data = json.loads(raw)
    sess_data["parts"][str(part_number)] = hashlib.md5(data).hexdigest()
    await valkey.setex(
        f"multipart:{upload_id}",
        MULTIPART_SESSION_TTL,
        json.dumps(sess_data),
    )
    part_key = f"multipart/{upload_id}/part_{part_number}"
    await storage.put(part_key, data, "application/octet-stream")
    return {"part_number": part_number, "etag": sess_data["parts"][str(part_number)]}


async def complete_multipart_upload(
    session: AsyncSession,
    storage: StorageBackend,
    media_repo: MediaRepository,
    community_id: uuid.UUID,
    valkey: Redis,
    user: User,
    upload_id: str,
) -> MediaResponse:
    """
    @brief Assemble parts, create Media record, enqueue transcode if video.

    @param session Async DB session for quota updates.
    @param storage Storage backend.
    @param media_repo Media repository.
    @param community_id Community UUID.
    @param valkey Valkey client.
    @param user The uploading user.
    @param upload_id Upload session ID.
    @return MediaResponse for the created media.
    """
    raw = await valkey.get(f"multipart:{upload_id}")
    if raw is None:
        raise NotFoundError(_("Upload session not found or expired"))
    sess_data = json.loads(raw)
    if sess_data["user_id"] != str(user.id):
        raise AuthorizationError(_("You do not own this upload session"))

    parts = sess_data["parts"]
    if not parts:
        raise AppError(
            code="NO_PARTS",
            message=_("No parts uploaded"),
            status_code=400,
        )
    sorted_parts = sorted(parts.keys(), key=int)
    chunks: list[bytes] = []
    for pn in sorted_parts:
        key = f"multipart/{upload_id}/part_{pn}"
        data = await storage.get(key)
        chunks.append(data)
        await storage.delete(key)
    await valkey.delete(f"multipart:{upload_id}")

    assembled = b"".join(chunks)
    total_size = len(assembled)
    content_type = sess_data["content_type"]
    filename = sess_data["filename"]

    ext = "mp4" if content_type in ALLOWED_VIDEO_TYPES else "jpg"
    if content_type == "image/jpeg":
        ext = "jpg"
    elif content_type == "image/png":
        ext = "png"
    elif content_type == "image/gif":
        ext = "gif"
    elif content_type == "image/webp":
        ext = "webp"
    elif content_type in ALLOWED_VIDEO_TYPES:
        ext = "mp4"
    storage_key = f"originals/{uuid.uuid4()}.{ext}"

    await storage.put(storage_key, assembled, content_type)
    await increment_storage_used(session, user.id, total_size)

    media = await media_repo.create(
        uploader_id=user.id,
        filename=filename,
        content_type=content_type,
        storage_key=storage_key,
        size_bytes=total_size,
        community_id=community_id,
    )

    if content_type in ALLOWED_VIDEO_TYPES:
        transcode_video.delay(str(media.id))
    else:
        generate_thumbnail.delay(str(media.id))

    return MediaResponse.model_validate(media)
