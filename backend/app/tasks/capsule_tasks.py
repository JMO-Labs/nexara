"""
@file capsule_tasks.py
@brief Celery beat task that opens due time capsules (every 10 minutes).
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
from app.repositories.time_capsule_repo import TimeCapsuleRepository
from app.services.notification_service import NotificationService
from app.services.time_capsule_service import TimeCapsuleService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _open_due_async() -> dict[str, int]:
    """@brief Run :meth:`TimeCapsuleService.open_due` in one transaction."""
    cid = uuid.UUID(get_settings().COMMUNITY_ID)
    async with async_session_factory() as session:
        notif = NotificationService(
            notification_repo=NotificationRepository(session),
            settings_repo=SettingsRepository(session),
            community_id=cid,
        )
        service = TimeCapsuleService(
            TimeCapsuleRepository(session), CommunityRepository(session), notif, cid
        )
        opened = await service.open_due(datetime.now(UTC))
        await session.commit()
    return {"opened": opened}


@celery_app.task(name="capsules.open_due", queue="notifications")
def open_due() -> dict[str, int]:
    """@brief Beat-driven entry: open capsules whose date has passed."""
    logger.info("capsules_open_due")
    return asyncio.run(_open_due_async())
