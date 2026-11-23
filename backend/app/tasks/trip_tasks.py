"""
@file trip_tasks.py
@brief Celery beat task for safe-arrival trips (every 5 minutes).
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
from app.repositories.trip_repo import TripRepository
from app.services.notification_service import NotificationService
from app.services.trip_service import TripService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _sweep_async() -> dict[str, int]:
    """@brief Run :meth:`TripService.sweep` in one transaction."""
    cid = uuid.UUID(get_settings().COMMUNITY_ID)
    async with async_session_factory() as session:
        notif = NotificationService(
            notification_repo=NotificationRepository(session),
            settings_repo=SettingsRepository(session),
            community_id=cid,
        )
        service = TripService(TripRepository(session), CommunityRepository(session), notif, cid)
        result = await service.sweep(datetime.now(UTC))
        await session.commit()
    return result


@celery_app.task(name="trips.sweep", queue="notifications")
def sweep() -> dict[str, int]:
    """@brief Beat-driven entry: overdue alerts and auto-end."""
    logger.info("trips_sweep")
    return asyncio.run(_sweep_async())
