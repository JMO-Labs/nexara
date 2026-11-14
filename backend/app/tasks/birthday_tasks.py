"""
@file birthday_tasks.py
@brief Celery task sending daily birthday reminders across all communities.

Routed to the ``notifications`` queue.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.repositories.birthday_repo import BirthdayRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.post_repo import PostRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.birthday_service import BirthdayService
from app.services.notification_service import NotificationService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _send_birthday_reminders_async() -> dict[str, int]:
    """@brief Run BirthdayService for every community with a birthday today."""
    today = datetime.now(UTC).date()
    auto_post = get_settings().BIRTHDAY_AUTO_POST
    total = 0
    async with async_session_factory() as session:
        repo = BirthdayRepository(session)
        for community_id in await repo.list_community_ids_with_birthday(today.month, today.day):
            notif = NotificationService(
                notification_repo=NotificationRepository(session),
                settings_repo=SettingsRepository(session),
                community_id=community_id,
            )
            service = BirthdayService(
                repo, notif, PostRepository(session), community_id, auto_post=auto_post
            )
            total += await service.send_reminders(today)
        await session.commit()
    return {"sent": total}


@celery_app.task(
    name="app.tasks.birthday_tasks.send_birthday_reminders",
    queue="notifications",
)
def send_birthday_reminders() -> dict[str, int]:
    """@brief Beat-driven entry: send today's birthday reminders."""
    logger.info("send_birthday_reminders")
    return asyncio.run(_send_birthday_reminders_async())
