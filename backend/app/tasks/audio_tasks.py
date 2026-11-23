"""
@file audio_tasks.py
@brief Celery task ``transcode_audio``: voice recordings to AAC 96 kbps ``.m4a``.

Clips longer than 15 minutes are ``rejected`` (error ``AUDIO_TOO_LONG``) and
their stored original is removed. Routed to the ``media`` queue.
"""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
import uuid
from pathlib import Path

import structlog
from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.transcode import extract_video_metadata
from app.db.session import async_session_factory
from app.repositories.media_repo import MediaRepository
from app.services.storage.factory import get_storage_backend
from app.services.storage.quota import decrement_storage_used, increment_storage_used
from app.tasks.celery_app import celery_app
from app.tasks.media_tasks import _invalidate_ready

logger = structlog.get_logger(__name__)

MAX_AUDIO_SECS = 900
"""@brief Longest accepted recording (15 minutes)."""


def build_audio_command(src: str, dst: str) -> list[str]:
    """@return ffmpeg argv: drop video, AAC 96 kbps, faststart ``.m4a``."""
    return ["ffmpeg", "-i", src, "-vn", "-c:a", "aac", "-b:a", "96k",
            "-movflags", "+faststart", "-y", dst]  # fmt: skip


def probe_duration(path: str) -> float:
    """@return Duration of an audio file in seconds (ffprobe)."""
    return float(extract_video_metadata(path)["duration_secs"])


async def _fail(
    repo: MediaRepository, session: AsyncSession, uid: uuid.UUID, status: str
) -> dict[str, str]:
    """@brief Persist a terminal non-ready status and return it."""
    await repo.update_status(uid, status)
    await session.commit()
    return {"status": status}


async def _transcode_audio_async(media_id: str) -> dict[str, str]:
    """@brief Download, probe, transcode, store and mark the media ready."""
    try:
        uid = uuid.UUID(media_id)
    except ValueError:
        return {"status": "error"}
    storage = get_storage_backend(get_settings())
    async with async_session_factory() as session:
        repo = MediaRepository(session)
        media = await repo.get(uid)
        if media is None:
            return {"status": "error"}
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = str(Path(tmp, "in")), str(Path(tmp, "out.m4a"))
            try:
                Path(src).write_bytes(await storage.get(media.storage_key))
                if probe_duration(src) > MAX_AUDIO_SECS:
                    logger.warning("audio_rejected", media_id=media_id, error="AUDIO_TOO_LONG")
                    await storage.delete(media.storage_key)
                    await decrement_storage_used(session, media.uploader_id, media.size_bytes)
                    return await _fail(repo, session, uid, "rejected")
                subprocess.run(build_audio_command(src, dst), capture_output=True, check=True,
                               timeout=900)  # fmt: skip
                duration = probe_duration(dst)
                data = Path(dst).read_bytes()
                await storage.delete(media.storage_key)
                await storage.put(media.storage_key, data, "audio/mp4")
            except Exception as exc:
                logger.error("transcode_audio_failed", media_id=media_id, error=str(exc))
                return await _fail(repo, session, uid, "error")
        if len(data) != media.size_bytes:
            await decrement_storage_used(session, media.uploader_id, media.size_bytes)
            await increment_storage_used(session, media.uploader_id, len(data))
        media.content_type = "audio/mp4"
        await repo.update_status(uid, "ready", duration_secs=duration, size_bytes=len(data))
        await session.commit()
        await _invalidate_ready(media.community_id, media.uploader_id)
    return {"status": "processed"}


@celery_app.task(
    bind=True,
    name="app.tasks.media_tasks.transcode_audio",
    max_retries=1,
    queue="media",
    time_limit=1200,
    soft_time_limit=1000,
)
def transcode_audio(self: Task, media_id: str) -> dict[str, str]:
    """
    @brief Transcode an uploaded recording to ``.m4a`` and set ``duration_secs``.
    @param media_id UUID string of the media row.
    @return ``{"status": "processed" | "error" | "rejected"}``.
    """
    try:
        return asyncio.run(_transcode_audio_async(media_id))
    except Exception as exc:
        logger.error("transcode_audio_crashed", media_id=media_id, error=str(exc))
        raise self.retry(exc=exc) from exc
