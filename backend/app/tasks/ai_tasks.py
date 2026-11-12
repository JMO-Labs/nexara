"""
@file ai_tasks.py
@brief Celery tasks for AI enrichment (OCR). Routed to the ``media`` queue.
"""

from __future__ import annotations

import asyncio
import uuid

import structlog

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.repositories.media_ai_repo import MediaAIRepository
from app.repositories.media_repo import MediaRepository
from app.services.ai.ocr import run_ocr
from app.services.ai.provider import get_ai_provider
from app.services.storage.factory import get_storage_backend
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _ocr_async(media_id: uuid.UUID, community_id: uuid.UUID) -> str:
    settings = get_settings()
    async with async_session_factory() as session:
        status = await run_ocr(
            media_id,
            community_id,
            media_repo=MediaRepository(session),
            ai_repo=MediaAIRepository(session),
            storage=get_storage_backend(settings),
            provider=get_ai_provider(settings),
        )
        await session.commit()
    return status


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.ai_tasks.ocr_process_image",
    soft_time_limit=3500,
    time_limit=3600,
)
def ocr_process_image(media_id: str, community_id: str) -> dict[str, str]:
    """
    @brief Extract text from an uploaded image (best-effort, never fails upload).
    @param media_id Media UUID string.
    @param community_id Community UUID string.
    @return Dict with the OCR status.
    """
    status = asyncio.run(_ocr_async(uuid.UUID(media_id), uuid.UUID(community_id)))
    return {"status": status}
