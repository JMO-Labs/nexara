"""@file gallery_tasks.py
@brief Celery tasks for gallery reminders and batched activity notifications.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.db.session import async_session_factory
from app.repositories.gallery_repo import GalleryRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.notification_service import NotificationService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.gallery_tasks.gallery_batch_notifications", queue="notifications")
def gallery_batch_notifications() -> dict[str, int]:
    return asyncio.run(_batch_notifications())


async def _batch_notifications() -> dict[str, int]:
    sent = 0
    async with async_session_factory() as session:
        gallery_repo = GalleryRepository(session)
        now = datetime.now(UTC)
        since = now - timedelta(minutes=60)
        active = await gallery_repo.list_with_recent_activity(since=since, threshold=5)
        for gallery, count in active:
            notif = NotificationService(
                notification_repo=NotificationRepository(session),
                settings_repo=SettingsRepository(session),
                community_id=gallery.community_id,
            )
            subscribers = await gallery_repo.list_subscribers(gallery.id)
            for user_id in subscribers:
                payload = {
                    "gallery_id": str(gallery.id),
                    "new_items": count,
                    "gallery_title": gallery.title,
                    "activity": "new_items",
                    "actor_name": "",
                    "message": f"{count} new items in {gallery.title}",
                    "link": f"/app/galleries/{gallery.id}",
                }
                await notif.notify(
                    user_id=user_id,
                    type="gallery_activity",
                    payload=payload,
                )
                sent += 1
        await session.commit()
    return {"sent": sent}
