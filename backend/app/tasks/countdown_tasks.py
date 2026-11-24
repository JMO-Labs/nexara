"""
@file countdown_tasks.py
@brief Hourly countdown reminders (7 days, 1 day, day-of), per viewer timezone.

Routed to the ``notifications`` queue.
"""

from __future__ import annotations

import asyncio
import uuid

import structlog

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.repositories.countdown_repo import CountdownRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.countdown_service import CountdownService
from app.services.notification_service import NotificationService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _run() -> dict[str, int]:
    cid = uuid.UUID(get_settings().COMMUNITY_ID)
    async with async_session_factory() as session:
        notifier = NotificationService(
            notification_repo=NotificationRepository(session),
            settings_repo=SettingsRepository(session),
            community_id=cid,
        )
        sent = await CountdownService(CountdownRepository(session), cid, notifier).send_reminders()
        await session.commit()
    return {"sent": sent}


@celery_app.task(name="app.tasks.countdown_tasks.send_countdown_reminders", queue="notifications")
def send_countdown_reminders() -> dict[str, int]:
    """@brief Beat-driven entry: send due countdown reminders."""
    logger.info("send_countdown_reminders")
    return asyncio.run(_run())
