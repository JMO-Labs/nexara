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


async def _sassybot_async(post_id: uuid.UUID, community_id: uuid.UUID, force: bool) -> bool:
    from app.repositories.comment_repo import CommentRepository
    from app.repositories.sassybot_repo import SassybotRepository
    from app.services.ai.sassybot_runner import run_sassybot
    from app.services.ai.sassybot_service import SassybotService
    from app.services.realtime.event_bus import event_bus

    settings = get_settings()
    provider = get_ai_provider(settings)
    if provider is None or not settings.SASSYBOT_USER_ID:
        return False
    bot_id = uuid.UUID(settings.SASSYBOT_USER_ID)
    async with async_session_factory() as session:
        repo = SassybotRepository(session)
        service = SassybotService(repo, provider, get_storage_backend(settings), bot_id)
        created = await run_sassybot(
            post_id,
            community_id,
            force=force,
            service=service,
            repo=repo,
            comment_repo=CommentRepository(session),
            bot_user_id=bot_id,
            event_bus=event_bus,
        )
        await session.commit()
    return created


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.ai_tasks.sassybot_comment_task",
    soft_time_limit=120,
    time_limit=180,
)
def sassybot_comment_task(post_id: str, community_id: str, force: bool = False) -> dict[str, bool]:
    """
    @brief Maybe post a Sassybot comment on a post (best-effort; AI errors are skipped).
    @param post_id Post UUID string.
    @param community_id Community UUID string.
    @param force True when @sassybot was mentioned (bypasses probability/invoke-only).
    @return Dict with ``created``.
    """
    created = asyncio.run(_sassybot_async(uuid.UUID(post_id), uuid.UUID(community_id), force))
    return {"created": created}
