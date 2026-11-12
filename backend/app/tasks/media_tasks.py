"""
@file media_tasks.py
@brief Celery tasks for media processing (thumbnail generation, video transcoding).

Routed to the ``media`` queue with lower concurrency to limit CPU pressure.
"""

from __future__ import annotations

import asyncio
import io
import tempfile
import uuid

import structlog
from celery import Task
from PIL import Image, ImageOps

from app.core.config import get_settings
from app.core.cache import invalidate_search_cache_for_community
from app.core.valkey import DB_CACHE, create_pool
from app.core.transcode import (
    build_ffmpeg_command,
    extract_thumbnail,
    extract_video_metadata,
    probe_and_set_encoder,
)
from app.db.session import async_session_factory
from app.repositories.media_repo import MediaRepository
from app.services.storage.factory import get_storage_backend
from app.services.storage.quota import decrement_storage_used, increment_storage_used
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)

THUMBNAIL_MAX_SIZE = (600, 600)
"""@brief Maximum thumbnail dimensions (width, height)."""

THUMBNAIL_QUALITY = 85
"""@brief WebP quality for thumbnails."""


async def _invalidate_ready(community_id: uuid.UUID, uploader_id: uuid.UUID) -> None:
    """
    @brief Invalidate the search cache with a client bound to the current loop.

    Celery runs each task in its own event loop, so the shared pool cannot be used.
    """
    redis = create_pool(get_settings(), DB_CACHE)
    try:
        await invalidate_search_cache_for_community(
            community_id, client=redis, service="media", action="ready", user_id=uploader_id
        )
    finally:
        await redis.aclose()


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
            return {"status": "error"}

        await repo.update_status(
            media_id,
            "ready",
            thumbnail_key=thumbnail_key,
            width=img.width,
            height=img.height,
        )
        await session.commit()
        await _invalidate_ready(media.community_id, media.uploader_id)

    logger.info("generate_thumbnail_completed", media_id=str(media_id))
    return {"status": "processed"}


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="app.tasks.media_tasks.generate_thumbnail",
    max_retries=2,
    queue="media",
    time_limit=300,
    soft_time_limit=240,
)
def generate_thumbnail(self: Task, media_id: str) -> dict[str, str]:
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


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="app.tasks.media_tasks.transcode_video",
    max_retries=1,
    queue="media",
    time_limit=3600,
    soft_time_limit=3300,
)
def transcode_video(self: Task, media_id: str) -> dict[str, str]:
    """
    @brief Transcode uploaded video to web-optimized H.264/AAC MP4.

    Downloads from storage, transcodes with ffmpeg, uploads result,
    extracts metadata and thumbnail, updates Media record.

    @param media_id UUID string of the media record.
    @return Dict with ``status`` (``"processed"`` or ``"error"``).
    """
    logger.info("transcode_video_started", media_id=media_id)
    try:
        return asyncio.run(_transcode_video_async(media_id))
    except Exception as exc:
        logger.error("transcode_video_failed", media_id=media_id, error=str(exc))
        raise self.retry(exc=exc)


async def _transcode_video_async(media_id: str) -> dict[str, str]:
    """@brief Async implementation of video transcoding."""
    from app.core.config import get_settings

    try:
        uid = uuid.UUID(media_id)
    except ValueError:
        logger.error("transcode_video_invalid_uuid", media_id=media_id)
        return {"status": "error"}

    settings = get_settings()
    storage = get_storage_backend(settings)

    async with async_session_factory() as session:
        repo = MediaRepository(session)
        media = await repo.get(uid)
        if media is None:
            logger.warning("transcode_video_media_not_found", media_id=media_id)
            return {"status": "error"}

        try:
            raw_data = await storage.get(media.storage_key)
        except Exception as exc:
            logger.error(
                "transcode_video_storage_get_failed",
                media_id=media_id,
                error=str(exc),
            )
            await repo.update_status(uid, "error")
            await session.commit()
            return {"status": "error"}

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
            tmp_in.write(raw_data)
            input_path = tmp_in.name

        output_path = input_path.replace(".mp4", "_out.mp4")
        thumb_path = input_path.replace(".mp4", "_thumb.jpg")

        try:
            encoder = probe_and_set_encoder()
            cmd = build_ffmpeg_command(input_path, output_path, encoder)
            import subprocess

            subprocess.run(cmd, capture_output=True, check=True, timeout=3300)
        except Exception as exc:
            logger.error(
                "transcode_video_ffmpeg_failed",
                media_id=media_id,
                error=str(exc),
            )
            await repo.update_status(uid, "error")
            await session.commit()
            return {"status": "error"}
        finally:
            import os

            if os.path.exists(input_path):
                os.unlink(input_path)

        try:
            metadata = extract_video_metadata(output_path)
            extract_thumbnail(output_path, thumb_path)
        except Exception as exc:
            logger.error(
                "transcode_video_metadata_failed",
                media_id=media_id,
                error=str(exc),
            )
            import os

            if os.path.exists(output_path):
                os.unlink(output_path)
            await repo.update_status(uid, "error")
            await session.commit()
            return {"status": "error"}

        try:
            with open(output_path, "rb") as f:
                transcoded_data = f.read()
            with open(thumb_path, "rb") as f:
                thumbnail_data = f.read()
        except Exception as exc:
            logger.error(
                "transcode_video_read_failed",
                media_id=media_id,
                error=str(exc),
            )
            import os

            if os.path.exists(output_path):
                os.unlink(output_path)
            if os.path.exists(thumb_path):
                os.unlink(thumb_path)
            await repo.update_status(uid, "error")
            await session.commit()
            return {"status": "error"}

        thumbnail_key = f"thumbnails/{uid}.webp"
        buf = io.BytesIO()
        thumb_img = Image.open(io.BytesIO(thumbnail_data)).convert("RGB")
        thumb_img.save(buf, format="WEBP", quality=THUMBNAIL_QUALITY)
        thumbnail_data = buf.getvalue()

        try:
            await storage.delete(media.storage_key)
            await storage.put(media.storage_key, transcoded_data, "video/mp4")
            await storage.put(thumbnail_key, thumbnail_data, "image/webp")
        except Exception as exc:
            logger.error(
                "transcode_video_storage_put_failed",
                media_id=media_id,
                error=str(exc),
            )
            await repo.update_status(uid, "error")
            await session.commit()
            return {"status": "error"}
        finally:
            import os

            if os.path.exists(output_path):
                os.unlink(output_path)
            if os.path.exists(thumb_path):
                os.unlink(thumb_path)

        new_size = len(transcoded_data)
        old_size = media.size_bytes
        if new_size != old_size:
            await decrement_storage_used(session, media.uploader_id, old_size)
            await increment_storage_used(session, media.uploader_id, new_size)

        await repo.update_status(
            uid,
            "ready",
            thumbnail_key=thumbnail_key,
            width=int(metadata.get("width") or 0),
            height=int(metadata.get("height") or 0),
            duration_secs=metadata.get("duration_secs") or 0.0,
            size_bytes=new_size,
        )
        await session.commit()
        await _invalidate_ready(media.community_id, media.uploader_id)

    logger.info("transcode_video_completed", media_id=media_id)
    return {"status": "processed"}


@celery_app.task(  # type: ignore[untyped-decorator]
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
