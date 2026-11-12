"""
@file mention_notify.py
@brief Notify users @mentioned in post/comment content, scoped to one community.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import _
from app.models.user import User
from app.services import mentions

if TYPE_CHECKING:
    from app.services.notification_service import NotificationService


async def notify_mentions(
    session: AsyncSession,
    notification: NotificationService,
    community_id: uuid.UUID,
    content: str,
    actor: User,
    post_id: uuid.UUID,
) -> None:
    """
    @brief Notify users @mentioned in content (never the actor, same community only).
    @param session DB session.
    @param notification Notification service.
    @param community_id Community scope for the username lookup.
    @param content Text containing potential @mentions.
    @param actor Author of the content.
    @param post_id Post UUID for the notification link.
    """
    usernames = mentions.extract(content)
    if not usernames:
        return
    stmt = select(User).where(
        User.username.in_(usernames),
        User.community_id == community_id,
        User.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    for mentioned in result.scalars().all():
        if mentioned.id == actor.id:
            continue
        await notification.notify(
            user_id=mentioned.id,
            type="mention",
            payload={
                "post_id": str(post_id),
                "actor_name": actor.display_name,
                "message": _("%(user)s mentioned you in a post") % {"user": actor.display_name},
                "link": f"/app/post/{post_id}",
            },
            actor_id=actor.id,
        )
