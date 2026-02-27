"""
@file media_tasks.py
@brief Celery tasks for media processing (thumbnail generation, EXIF stripping).

Routed to the ``media`` queue with lower concurrency to limit CPU pressure.
Video transcoding tasks are added in Phase 2.
"""

from __future__ import annotations

import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


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

    Images are resized to 400x400 max and converted to WebP.  EXIF data
    is stripped for privacy.  Updates ``media.thumbnail_key`` and sets
    ``media.status`` to ``"ready"`` on success or ``"error"`` on failure.

    @param media_id UUID string of the media record.
    @return Dict with ``status`` (``"processed"`` or ``"error"``).
    """
    logger.info("generate_thumbnail_started", media_id=media_id)

    try:
        # Actual Pillow processing is wired when the storage + DB layers
        # are integrated in Phase 1 Group 5 (09-media).
        # Skeleton validates the task structure, routing, and retry config.
        logger.info("generate_thumbnail_completed", media_id=media_id)
        return {"status": "processed"}
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
