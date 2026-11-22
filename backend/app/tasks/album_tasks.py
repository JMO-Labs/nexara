"""
@file album_tasks.py
@brief Celery beat task (hourly) reminding attendees to share event photos.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import structlog

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.repositories.album_repo import AlbumRepository
from app.repositories.community_repo import CommunityRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.album_service import AlbumService
from app.services.notification_service import NotificationService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _remind_async() -> dict[str, int]:
    """@brief Run :meth:`AlbumService.remind_due` in one transaction."""
    cid = uuid.UUID(get_settings().COMMUNITY_ID)
    async with async_session_factory() as session:
        notif = NotificationService(
            notification_repo=NotificationRepository(session),
            settings_repo=SettingsRepository(session),
            community_id=cid,
        )
        service = AlbumService(AlbumRepository(session), CommunityRepository(session), notif, cid)
        count = await service.remind_due(datetime.now(UTC))
        await session.commit()
    return {"reminded": count}


@celery_app.task(name="albums.remind", queue="notifications")
def remind() -> dict[str, int]:
    """@brief Beat-driven entry: send photo-share reminders."""
    logger.info("albums_remind")
    return asyncio.run(_remind_async())
