"""
@file chore_tasks.py
@brief Beat task ``chores.advance_due``: roll due repeating chores to the next person.

Idempotent: each item is locked (``SKIP LOCKED``) and only advanced while
``next_due_at <= now``; advancing moves ``next_due_at`` past ``now``.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.community import Community
from app.models.list import List
from app.repositories.chore_repo import ChoreRepository
from app.repositories.list_activity_repo import ListActivityRepository
from app.repositories.list_assignment_repo import ListAssignmentRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.chore_service import ChoreService
from app.services.list_activity_service import ListActivityService
from app.services.notification_service import NotificationService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


def _service(session: AsyncSession, community: Community) -> ChoreService:
    cid = community.id
    lists = ListRepository(session)
    return ChoreService(
        ChoreRepository(session),
        ListItemRepository(session),
        lists,
        ListAssignmentRepository(session),
        ListActivityService(ListActivityRepository(session), lists, cid),
        community,
        NotificationService(NotificationRepository(session), SettingsRepository(session), cid),
    )


async def advance_due(session: AsyncSession, now: datetime) -> int:
    """
    @brief Advance every due chore once; skip communities with ``chores`` off.
    @param session Async DB session.
    @param now Current time (UTC).
    @return Number of items advanced.
    """
    repo = ChoreRepository(session)
    services: dict[uuid.UUID, ChoreService] = {}
    done = 0
    for item_id in await repo.due_item_ids(now):
        item = await repo.lock_due(item_id, now)
        if item is None:
            continue
        lst = await session.get(List, item.list_id)
        community = await session.get(Community, lst.community_id) if lst else None
        if community is None:
            continue
        svc = services.setdefault(community.id, _service(session, community))
        if not svc.enabled():
            await session.rollback()
            continue
        try:
            await svc.advance(item, now)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("chore_advance_failed", item_id=str(item_id))
            continue
        done += 1
    return done


async def _run() -> dict[str, int]:
    async with async_session_factory() as session:
        return {"advanced": await advance_due(session, datetime.now(UTC))}


@celery_app.task(name="chores.advance_due", queue="maintenance")
def advance_due_task() -> dict[str, int]:
    """@brief Beat-driven entry (every 15 minutes)."""
    logger.info("chores_advance_due")
    return asyncio.run(_run())
