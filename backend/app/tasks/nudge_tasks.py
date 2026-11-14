"""
@file nudge_tasks.py
@brief Celery task for automated gentle nudges (daily, ``maintenance`` queue).
"""

from __future__ import annotations

import asyncio
import uuid

import structlog

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.repositories.notification_repo import NotificationRepository
from app.repositories.nudge_repo import NudgeRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.user_repo import UserRepository
from app.services.notification_service import NotificationService
from app.services.nudge_service import NudgeService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _send_gentle_nudges_async() -> dict[str, int]:
    """@brief Run :meth:`NudgeService.send_gentle_nudges` in one transaction."""
    community_id = uuid.UUID(get_settings().COMMUNITY_ID)
    async with async_session_factory() as session:
        notif = NotificationService(
            notification_repo=NotificationRepository(session),
            settings_repo=SettingsRepository(session),
            community_id=community_id,
        )
        service = NudgeService(
            NudgeRepository(session), UserRepository(session), notif, community_id
        )
        sent = await service.send_gentle_nudges(community_id)
        await session.commit()
    return {"sent": sent}


@celery_app.task(
    name="app.tasks.nudge_tasks.send_gentle_nudges",
    queue="maintenance",
)
def send_gentle_nudges() -> dict[str, int]:
    """@brief Beat-driven entry: nudge users inactive for over 14 days."""
    logger.info("send_gentle_nudges")
    return asyncio.run(_send_gentle_nudges_async())
