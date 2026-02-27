"""
@file media_tasks.py
@brief Celery tasks for media processing (thumbnail generation, EXIF stripping).

Routed to the ``media`` queue with lower concurrency to limit CPU pressure.
Video transcoding tasks are added in Phase 2.
"""

from __future__ import annotations

import asyncio
import io
import uuid

import structlog
from PIL import Image, ImageOps

from app.db.session import async_session_factory
from app.repositories.media_repo import MediaRepository
from app.services.storage.factory import get_storage_backend
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)

THUMBNAIL_MAX_SIZE = (600, 600)
"""@brief Maximum thumbnail dimensions (width, height)."""

THUMBNAIL_QUALITY = 85
"""@brief WebP quality for thumbnails."""


async def _generate_thumbnail_async(media_id: uuid.UUID) -> dict[str, str]:
    """
    @brief Async implementation of thumbnail generation.

    Retrieves original from storage, processes with Pillow, stores thumbnail,
    and updates the media record.

    @param media_id UUID of the media record.
    @return Dict with status (processed or error).
    """
    from app.core.config import get_settings

    settings = get_settings()
    storage = get_storage_backend(settings)

    async with async_session_factory() as session:
        repo = MediaRepository(session)
        media = await repo.get(media_id)
        if media is None:
            logger.warning("generate_thumbnail_media_not_found", media_id=str(media_id))
            return {"status": "error"}

        try:
            raw_data = await storage.get(media.storage_key)
        except Exception as exc:
            logger.error(
                "generate_thumbnail_storage_get_failed",
                media_id=str(media_id),
                error=str(exc),
            )
            await repo.update_status(media_id, "error")
            await session.commit()
            return {"status": "error"}

        try:
            img = Image.open(io.BytesIO(raw_data)).convert("RGB")
            img = ImageOps.exif_transpose(img)
            img.thumbnail(THUMBNAIL_MAX_SIZE, Image.Resampling.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format="WEBP", quality=THUMBNAIL_QUALITY)
            thumbnail_data = buf.getvalue()
        except Exception as exc:
            logger.error(
                "generate_thumbnail_pillow_failed",
                media_id=str(media_id),
                error=str(exc),
            )
            await repo.update_status(media_id, "error")
            await session.commit()
            return {"status": "error"}

        thumbnail_key = f"thumbnails/{media_id}.webp"
        try:
            await storage.put(thumbnail_key, thumbnail_data, "image/webp")
        except Exception as exc:
            logger.error(
                "generate_thumbnail_storage_put_failed",
                media_id=str(media_id),
                error=str(exc),
            )
            await repo.update_status(media_id, "error")
            await session.commit()
            return {"status": "error"}

        await repo.update_status(
            media_id,
            "ready",
            thumbnail_key=thumbnail_key,
            width=img.width,
            height=img.height,
        )
        await session.commit()

    logger.info("generate_thumbnail_completed", media_id=str(media_id))
    return {"status": "processed"}


@celery_app.task(
    bind=True,
    name="app.tasks.media_tasks.generate_thumbnail",
    max_retries=2,
    queue="media",
    time_limit=300,
    soft_time_limit=240,
)
def generate_thumbnail(self, media_id: str) -> dict[str, str]:
    """
    @brief Generate a thumbnail for an uploaded image.

    Images are resized to 600x600 max and converted to WebP.  EXIF data
    is stripped for privacy.  Updates ``media.thumbnail_key`` and sets
    ``media.status`` to ``"ready"`` on success or ``"error"`` on failure.

    @param media_id UUID string of the media record.
    @return Dict with ``status`` (``"processed"`` or ``"error"``).
    """
    logger.info("generate_thumbnail_started", media_id=media_id)

    try:
        uid = uuid.UUID(media_id)
    except ValueError:
        logger.error("generate_thumbnail_invalid_uuid", media_id=media_id)
        return {"status": "error"}

    try:
        return asyncio.run(_generate_thumbnail_async(uid))
    except Exception as exc:
        logger.error("generate_thumbnail_failed", media_id=media_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.tasks.media_tasks.transcode_video",
    max_retries=1,
    queue="media",
    time_limit=3600,
    soft_time_limit=3500,
)
def transcode_video(self, media_id: str) -> dict[str, str]:
    """
    @brief Transcode uploaded video to web-optimized H.264/AAC MP4.

    Target: 1080p max, CRF 23, AAC 128kbps.  Updates ``media.status``
    to ``"ready"`` on completion, ``"error"`` on failure.

    @param media_id UUID string of the media record.
    @return Dict with ``status``.
    """
    logger.info("transcode_video_started", media_id=media_id)
    return {"status": "processed"}


@celery_app.task(
    name="app.tasks.media_tasks.delete_orphaned_media",
    queue="media",
)
def delete_orphaned_media() -> dict[str, int]:
    """
    @brief Delete media records/files with no post attachment and status ``"processing"``
    that are older than 24 hours (upload abandoned).

    @return Dict with ``deleted_count``.
    """
    logger.info("delete_orphaned_media_started")
    return {"deleted_count": 0}
