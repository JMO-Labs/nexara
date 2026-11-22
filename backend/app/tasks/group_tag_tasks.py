"""
@file group_tag_tasks.py
@brief Celery fan-out for @group tags (notifications queue), so a tag on a
       large group never slows the request that created the post.
"""

from __future__ import annotations

import asyncio
import uuid

import structlog

from app.db.session import async_session_factory
from app.repositories.group_tag_repo import GroupTagRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.group_tag_service import GroupTagService
from app.services.notification_service import NotificationService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _fan_out(
    community_id: uuid.UUID,
    subgroup_id: uuid.UUID,
    post_id: uuid.UUID,
    actor_id: uuid.UUID,
    actor_name: str,
    on_comment: bool,
) -> int:
    async with async_session_factory() as session:
        notifier = NotificationService(
            notification_repo=NotificationRepository(session),
            settings_repo=SettingsRepository(session),
            community_id=community_id,
        )
        svc = GroupTagService(GroupTagRepository(session), community_id)
        # ponytail: one transaction per tag; batch commits if groups reach thousands.
        n = await svc.fan_out(notifier, subgroup_id, post_id, actor_id, actor_name, on_comment)
        await session.commit()
        return n


@celery_app.task(name="app.tasks.group_tag_tasks.notify_group_tag", queue="notifications")
def notify_group_tag(
    community_id: str,
    subgroup_id: str,
    post_id: str,
    actor_id: str,
    actor_name: str,
    on_comment: bool = False,
) -> int:
    """@brief Notify a tagged group's members."""
    n = asyncio.run(
        _fan_out(
            uuid.UUID(community_id),
            uuid.UUID(subgroup_id),
            uuid.UUID(post_id),
            uuid.UUID(actor_id),
            actor_name,
            on_comment,
        )
    )
    logger.info("group_tag_fanout", subgroup_id=subgroup_id, recipients=n)
    return n
