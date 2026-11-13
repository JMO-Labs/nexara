"""
@file list_tasks.py
@brief Celery tasks expiring lists and reminding members before expiry.

Both tasks are routed to the ``maintenance`` queue and scheduled by Beat
(02:00 sweep, 08:00 reminders).  Rows are processed in batches so the
``list`` table is never locked as a whole.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from typing import Any

import structlog
from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.list import List, ListMember
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.notification_service import NotificationService
from app.services.realtime import events
from app.services.realtime.event_bus import event_bus
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)

BATCH_SIZE = 100
NotifierFactory = Callable[[uuid.UUID], Any]


async def _recipients(session: AsyncSession, lst: List) -> set[uuid.UUID]:
    """@brief Owner plus explicit members of a list."""
    rows = await session.scalars(select(ListMember.user_id).where(ListMember.list_id == lst.id))
    return {lst.owner_id, *rows.all()}


async def _notify_all(
    session: AsyncSession, notifier: Any, lst: List, message: str, bus_link: str
) -> None:
    for user_id in await _recipients(session, lst):
        await notifier.notify(
            user_id,
            "system",
            {"message": message, "link": bus_link, "target_id": str(lst.id)},
        )


def _batch_stmt(*conditions: Any, limit: int) -> Select[tuple[List]]:
    return (
        select(List)
        .where(List.status == "active", List.deleted_at.is_(None), *conditions)
        .order_by(List.expires_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


async def sweep_expired_lists(
    session: AsyncSession,
    notifier_for: NotifierFactory,
    bus: Any,
    batch_size: int = BATCH_SIZE,
) -> int:
    """
    @brief Mark lists past ``expires_at`` as expired, emit events, notify.

    @param session Async DB session.
    @param notifier_for Factory ``community_id -> NotificationService``.
    @param bus Event bus with ``emit``.
    @param batch_size Rows per transaction.
    @return Number of lists expired.
    """
    total = 0
    while True:
        now = datetime.now(UTC)
        stmt = _batch_stmt(List.expires_at.is_not(None), List.expires_at < now, limit=batch_size)
        batch = (await session.execute(stmt)).scalars().all()
        if not batch:
            return total
        for lst in batch:
            lst.status = "expired"
            await _notify_all(
                session,
                notifier_for(lst.community_id),
                lst,
                f"List '{lst.title}' has expired",
                f"/lists/{lst.id}",
            )
            target = events.CommunityTarget(community_id=lst.community_id)
            await bus.emit(events.list_expired(target, lst.id, lst.title))
        await session.commit()
        total += len(batch)


async def send_expiry_reminders(
    session: AsyncSession,
    notifier_for: NotifierFactory,
    bus: Any,
    batch_size: int = BATCH_SIZE,
) -> int:
    """
    @brief Remind owner/members of lists expiring within one day.

    Lists already reminded today (``notified_at`` >= start of today) are skipped.

    @param session Async DB session.
    @param notifier_for Factory ``community_id -> NotificationService``.
    @param bus Event bus (unused; kept for symmetry with the sweep).
    @param batch_size Rows per transaction.
    @return Number of lists reminded.
    """
    total = 0
    while True:
        now = datetime.now(UTC)
        today = datetime.combine(now.date(), time.min, tzinfo=UTC)
        stmt = _batch_stmt(
            List.expires_at.is_not(None),
            List.expires_at >= now,
            List.expires_at <= now + timedelta(days=1),
            or_(List.notified_at.is_(None), List.notified_at < today),
            limit=batch_size,
        )
        batch = (await session.execute(stmt)).scalars().all()
        if not batch:
            return total
        for lst in batch:
            await _notify_all(
                session,
                notifier_for(lst.community_id),
                lst,
                f"List '{lst.title}' expires within 24 hours",
                f"/lists/{lst.id}",
            )
            lst.notified_at = now
        await session.commit()
        total += len(batch)


def _notifier_factory(session: AsyncSession) -> NotifierFactory:
    def make(community_id: uuid.UUID) -> NotificationService:
        return NotificationService(
            notification_repo=NotificationRepository(session),
            settings_repo=SettingsRepository(session),
            community_id=community_id,
        )

    return make


async def _sweep_async() -> dict[str, int]:
    async with async_session_factory() as session:
        n = await sweep_expired_lists(session, _notifier_factory(session), event_bus)
    return {"expired": n}


async def _remind_async() -> dict[str, int]:
    async with async_session_factory() as session:
        n = await send_expiry_reminders(session, _notifier_factory(session), event_bus)
    return {"reminded": n}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.list_tasks.sweep_list_expirations",
    queue="maintenance",
)
def sweep_list_expirations() -> dict[str, int]:
    """@brief Beat-driven entry (02:00 UTC): expire overdue lists."""
    logger.info("sweep_list_expirations")
    return asyncio.run(_sweep_async())


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.list_tasks.dispatch_list_expiry_reminders",
    queue="maintenance",
)
def dispatch_list_expiry_reminders() -> dict[str, int]:
    """@brief Beat-driven entry (08:00 UTC): remind about lists expiring within a day."""
    logger.info("dispatch_list_expiry_reminders")
    return asyncio.run(_remind_async())
