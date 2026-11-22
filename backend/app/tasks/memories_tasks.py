"""
@file memories_tasks.py
@brief Hourly beat task: "on this day" reminder at 09:00 user-local (``default`` queue).
"""

from __future__ import annotations

import asyncio
import uuid

import structlog

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.repositories.community_repo import CommunityRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.post_memories_repo import PostMemoriesRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.user_repo import UserRepository
from app.services.memories_service import MemoriesService
from app.services.notification_service import NotificationService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _notify_on_this_day_async() -> dict[str, int]:
    """@brief Run :meth:`MemoriesService.notify_due` in one transaction."""
    cid = uuid.UUID(get_settings().COMMUNITY_ID)
    async with async_session_factory() as session:
        notif = NotificationService(
            notification_repo=NotificationRepository(session),
            settings_repo=SettingsRepository(session),
            community_id=cid,
        )
        svc = MemoriesService(
            PostMemoriesRepository(session),
            UserRepository(session),
            CommunityRepository(session),
            cid,
            notif,
        )
        sent = await svc.notify_due()
        await session.commit()
    return {"sent": sent}


@celery_app.task(name="app.tasks.memories_tasks.notify_on_this_day", queue="default")
def notify_on_this_day() -> dict[str, int]:
    """@brief Beat entry: remind users who have memories today."""
    logger.info("notify_on_this_day")
    return asyncio.run(_notify_on_this_day_async())
