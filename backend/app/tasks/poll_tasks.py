"""
@file poll_tasks.py
@brief Celery tasks for poll maintenance (closing expired polls).

Routed to the ``maintenance`` queue.
"""

from __future__ import annotations

import asyncio

import structlog

from app.db.session import async_session_factory
from app.repositories.poll_repo import PollRepository
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _close_expired_polls_async() -> dict[str, int]:
    """
    @brief Close all polls past their expires_at timestamp.

    @return Dict with closed_count.
    """
    async with async_session_factory() as session:
        repo = PollRepository(session)
        count = await repo.close_expired()
        await session.commit()
        return {"closed_count": count}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.poll_tasks.close_expired_polls",
    queue="maintenance",
)
def close_expired_polls() -> dict[str, int]:
    """
    @brief Close polls that have passed their expiry time.

    Runs every 60 seconds via Beat.

    @return Dict with closed_count.
    """
    logger.info("close_expired_polls")
    return asyncio.run(_close_expired_polls_async())
