"""
@file story_tasks.py
@brief Beat task ``stories.daily``: one reminder at day 14, expiry at day 30.

Idempotent: reminders are claimed by stamping ``reminded_at`` in one UPDATE,
and expiry only touches rows still open/declined.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import structlog

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.repositories.community_repo import CommunityRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.story_repo import StoryRepository
from app.services.notification_service import NotificationService
from app.services.story_service import StoryService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _daily_async(now: datetime) -> dict[str, int]:
    """@brief Run :meth:`StoryService.run_daily` in one transaction."""
    cid = uuid.UUID(get_settings().COMMUNITY_ID)
    async with async_session_factory() as session:
        notif = NotificationService(
            NotificationRepository(session), SettingsRepository(session), cid
        )
        service = StoryService(StoryRepository(session), CommunityRepository(session), notif, cid)
        out = await service.run_daily(now)
        await session.commit()
    return out


@celery_app.task(name="stories.daily", queue="notifications")
def daily() -> dict[str, int]:
    """@brief Beat-driven entry: remind at day 14, expire at day 30."""
    logger.info("stories_daily")
    return asyncio.run(_daily_async(datetime.now(UTC)))
