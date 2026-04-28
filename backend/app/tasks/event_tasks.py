"""
@file event_tasks.py
@brief Celery tasks for events — reminder dispatch and external feed sync.

- ``dispatch_event_reminders`` runs every 15 minutes via Beat. For each event
  starting within the next hour, sends ``event_reminder`` notifications to
  every user who RSVP'd ``attending`` or ``maybe`` (deduped per event).
- ``sync_subscriptions`` runs hourly. For each enabled subscription whose
  ``last_synced_at`` is past the configured interval, fetches the iCal feed
  and upserts events via :class:`EventService.sync_subscription`.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import structlog
from celery import Task

from app.db.session import async_session_factory
from app.repositories.event_repo import EventRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.event_service import EventService
from app.services.notification_service import NotificationService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)

REMINDER_LEAD_MIN = 60
"""@brief How many minutes ahead of starts_at to remind."""

REMINDER_INTERVAL_MIN = 15
"""@brief Beat cadence — must match celery_app schedule."""

SYNC_INTERVAL = timedelta(hours=1)
"""@brief Minimum interval between subscription syncs."""


async def _dispatch_reminders_async() -> dict[str, int]:
    """
    @brief Dispatch reminders for events starting in configurable offset windows.

    Loops over offsets {15, 60, 1440} minutes and dispatches reminders for events
    with matching reminder_offsets_minutes.
    """
    window_min = 7  # half-window: ± 7 minutes around each offset
    offsets = [15, 60, 1440]

    sent = 0
    async with async_session_factory() as session:
        repo = EventRepository(session)
        now = datetime.now(UTC)

        for offset in offsets:
            window_start = now + timedelta(minutes=offset - window_min)
            window_end = now + timedelta(minutes=offset + window_min)
            events = await repo.list_with_offset_in_range(offset, window_start, window_end)

            for event in events:
                notif = NotificationService(
                    notification_repo=NotificationRepository(session),
                    settings_repo=SettingsRepository(session),
                    community_id=event.community_id,
                )
                attendances = await repo.list_attendance(event.id)
                recipients = {a.user_id for a in attendances if a.status in ("attending", "maybe")}
                for user_id in recipients:
                    try:
                        await notif.notify(
                            user_id=user_id,
                            type="event_reminder",
                            payload={
                                "event_id": str(event.id),
                                "title": event.title,
                                "starts_at": event.starts_at.isoformat(),
                                "message": f"Reminder: {event.title} starts soon",
                                "link": f"/app/events/{event.id}",
                                "subject": f"Reminder: {event.title}",
                            },
                        )
                        sent += 1
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "event_reminder_failed",
                            event_id=str(event.id),
                            user_id=str(user_id),
                            error=str(exc),
                        )
        await session.commit()
    return {"reminders_sent": sent}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.event_tasks.dispatch_event_reminders",
    queue="notifications",
)
def dispatch_event_reminders() -> dict[str, int]:
    """@brief Beat-driven entry point for event reminders."""
    logger.info("dispatch_event_reminders")
    return asyncio.run(_dispatch_reminders_async())


async def _sync_subscriptions_async() -> dict[str, Any]:
    """@brief Pull-and-upsert iCal feeds for due subscriptions."""
    now = datetime.now(UTC)
    synced = 0
    failed = 0
    upserted_total = 0

    async with async_session_factory() as session:
        repo = EventRepository(session)
        due = await repo.list_subscriptions_due(now, SYNC_INTERVAL)

        for sub in due:
            if sub.source_type != "ical" or not sub.source_url:
                continue
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(sub.source_url)
                    resp.raise_for_status()
                    body = resp.content

                service = EventService(
                    event_repo=repo,
                    community_id=sub.community_id,
                    session=session,
                )
                upserted = await service.sync_subscription(sub, body)
                upserted_total += upserted
                synced += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "subscription_sync_failed",
                    sub_id=str(sub.id),
                    error=str(exc),
                )
                sub.sync_error = f"fetch_error: {exc}"
                failed += 1

        await session.commit()

    return {"synced": synced, "failed": failed, "events_upserted": upserted_total}


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="app.tasks.event_tasks.sync_subscriptions",
    queue="maintenance",
    max_retries=2,
)
def sync_subscriptions(self: Task) -> dict[str, Any]:
    """@brief Beat-driven entry point for subscription sync."""
    logger.info("sync_subscriptions")
    try:
        return asyncio.run(_sync_subscriptions_async())
    except Exception as exc:
        logger.exception("sync_subscriptions_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300)
