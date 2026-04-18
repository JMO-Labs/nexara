"""
@file link_preview_tasks.py
@brief Celery tasks for link preview scraping.
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import structlog

from app.db.session import async_session_factory
from app.repositories.link_preview_repo import LinkPreviewRepository
from app.services.link_preview_service import (
    detect_video_provider,
    is_safe_url,
    scrape_og_metadata,
)
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _scrape_link_preview_async(
    url: str,
    post_id: uuid.UUID | None,
    message_id: uuid.UUID | None,
) -> dict[str, str | int | bool]:
    """
    @brief Async implementation: scrape URL, store preview, link to post/message.

    @param url URL to scrape.
    @param post_id Optional post UUID to associate.
    @param message_id Optional message UUID to associate.
    @return Dict with status, preview_id, etc.
    """
    if not is_safe_url(url):
        logger.warning("scrape_link_preview_ssrf_rejected", url=url)
        return {"status": "rejected", "reason": "ssrf"}

    metadata = await scrape_og_metadata(url)
    video = detect_video_provider(url)
    provider_type, provider_id = video if video else (None, None)

    url_hash = hashlib.sha256(url.encode()).hexdigest()
    defaults = {
        "title": metadata.get("title") or "",
        "description": metadata.get("description"),
        "image_url": metadata.get("image_url"),
        "site_name": metadata.get("site_name"),
        "provider_type": provider_type,
        "provider_id": provider_id,
        "fetch_error": not metadata.get("title") and not metadata.get("description"),
        "expires_at": datetime.now(UTC) + timedelta(days=90),
    }

    async with async_session_factory() as session:
        repo = LinkPreviewRepository(session)
        preview, created = await repo.find_or_create(url, url_hash, defaults)

        position = 0
        if post_id is not None:
            await repo.create_post_link(post_id, preview.id, position)
            position += 1
        if message_id is not None:
            await repo.create_message_link(message_id, preview.id, position)

        await session.commit()

    logger.info(
        "scrape_link_preview_completed",
        url=url,
        preview_id=str(preview.id),
        created=created,
    )
    return {
        "status": "ok",
        "preview_id": str(preview.id),
        "created": created,
    }


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.link_preview_tasks.scrape_link_preview",
    queue="default",
)
def scrape_link_preview(
    url: str,
    post_id: str | None = None,
    message_id: str | None = None,
) -> dict[str, str | int | bool]:
    """
    @brief Scrape a URL for OG metadata and store the link preview.

    Optionally associates the preview with a post and/or chat message.
    SSRF protection rejects private/loopback/reserved IPs.

    @param url URL to scrape.
    @param post_id Optional post UUID string.
    @param message_id Optional message UUID string.
    @return Dict with status, preview_id, created.
    """
    logger.info("scrape_link_preview_started", url=url)

    pid: uuid.UUID | None = None
    mid: uuid.UUID | None = None
    if post_id:
        try:
            pid = uuid.UUID(post_id)
        except ValueError:
            logger.error("scrape_link_preview_invalid_post_id", post_id=post_id)
            return {"status": "error", "reason": "invalid_post_id"}
    if message_id:
        try:
            mid = uuid.UUID(message_id)
        except ValueError:
            logger.error("scrape_link_preview_invalid_message_id", message_id=message_id)
            return {"status": "error", "reason": "invalid_message_id"}

    try:
        return asyncio.run(_scrape_link_preview_async(url, pid, mid))
    except Exception as exc:
        logger.error("scrape_link_preview_failed", url=url, error=str(exc))
        raise
