"""
@file prompt_tasks.py
@brief Celery tasks for tradition prompts — daily firing and summary generation.

Routed to the ``maintenance`` queue.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.repositories.notification_repo import NotificationRepository
from app.repositories.post_repo import PostRepository
from app.repositories.prompt_repo import PromptRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.notification_service import NotificationService
from app.services.prompt_service import PromptService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


def _community_id() -> uuid.UUID:
    return uuid.UUID(get_settings().COMMUNITY_ID)


async def _fire_prompts_async() -> dict[str, int]:
    """@brief Run :meth:`PromptService.fire_due_prompts` for today."""
    today = datetime.now(UTC).date()
    community_id = _community_id()
    async with async_session_factory() as session:
        notif = NotificationService(
            notification_repo=NotificationRepository(session),
            settings_repo=SettingsRepository(session),
            community_id=community_id,
        )
        service = PromptService(
            prompt_repo=PromptRepository(session),
            post_repo=PostRepository(session),
            community_id=community_id,
            session=session,
            notification_service=notif,
        )
        fired = await service.fire_due_prompts(today)
        await session.commit()
    return {"fired": fired}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.prompt_tasks.fire_prompts",
    queue="maintenance",
)
def fire_prompts() -> dict[str, int]:
    """@brief Beat-driven entry: fire prompts whose schedule matches today."""
    logger.info("fire_prompts")
    return asyncio.run(_fire_prompts_async())


async def _generate_summaries_async() -> dict[str, int]:
    """@brief Run :meth:`PromptService.finalise_expired`."""
    community_id = _community_id()
    async with async_session_factory() as session:
        notif = NotificationService(
            notification_repo=NotificationRepository(session),
            settings_repo=SettingsRepository(session),
            community_id=community_id,
        )
        service = PromptService(
            prompt_repo=PromptRepository(session),
            post_repo=PostRepository(session),
            community_id=community_id,
            session=session,
            notification_service=notif,
        )
        finalised = await service.finalise_expired()
        await session.commit()
    return {"finalised": finalised}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.prompt_tasks.generate_summaries",
    queue="maintenance",
)
def generate_summaries() -> dict[str, int]:
    """@brief Beat-driven entry: finalise expired prompts and post summaries."""
    logger.info("generate_summaries")
    return asyncio.run(_generate_summaries_async())


async def _seed_builtin_prompts_async(prompts: list[dict[str, Any]]) -> dict[str, int]:
    """
    @brief Idempotently seed built-in prompts on first migration.

    Skips any prompt whose ``title`` already exists with ``source='builtin'``.
    """
    from sqlalchemy import select

    from app.models.prompt import Prompt

    community_id = _community_id()
    inserted = 0
    async with async_session_factory() as session:
        for entry in prompts:
            stmt = select(Prompt).where(
                Prompt.community_id == community_id,
                Prompt.title == entry["title"],
                Prompt.source == "builtin",
            )
            result = await session.execute(stmt)
            if result.scalar_one_or_none() is not None:
                continue
            session.add(
                Prompt(
                    community_id=community_id,
                    source="builtin",
                    **{k: v for k, v in entry.items() if k != "id"},
                )
            )
            inserted += 1
        await session.commit()
    return {"inserted": inserted}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.prompt_tasks.seed_builtin_prompts",
    queue="maintenance",
)
def seed_builtin_prompts() -> dict[str, int]:
    """@brief Load built-in prompts from data/builtin_prompts.json."""
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "data" / "builtin_prompts.json"
    if not path.exists():
        logger.warning("seed_builtin_prompts_missing_file", path=str(path))
        return {"inserted": 0}

    data = json.loads(path.read_text(encoding="utf-8"))
    return asyncio.run(_seed_builtin_prompts_async(data))
