"""
@file mention_tags.py
@brief Reusable service for syncing @mentions to tags and notifying newly tagged users.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable

import structlog

from app.core.i18n import _
from app.repositories.tag_repo import TagRepository
from app.services import mentions

logger = structlog.get_logger(__name__)


class MentionTagsService:
    """@brief Helper to sync mentions in text to tags and notify newly tagged users."""

    def __init__(self, tag_repo: TagRepository) -> None:
        """
        @param tag_repo TagRepository instance for tag operations.
        """
        self._tags = tag_repo

    async def sync_mentions(
        self,
        community_id: uuid.UUID,
        target_type: str,
        target_id: uuid.UUID,
        content: str,
        actor_id: uuid.UUID,
        actor_name: str,
        notify_callable: Callable[[uuid.UUID, str, dict[str, Any]], Any] | None = None,
        *,
        can_see: Callable[[uuid.UUID], Any] | None = None,
        link: str = "",
        label: str = "",
        fresh: bool = True,
    ) -> None:
        """
        @brief Extract mentions from text and sync user tags; notify newly tagged users.

        @param community_id Community UUID for scoping.
        @param target_type One of 'post', 'comment', 'media', 'list', 'event', 'chat_message'.
        @param target_id UUID of the target object (post, event, list, etc).
        @param content Plain text or markdown to extract mentions from.
        @param actor_id User ID of who is creating/editing (never tagged themselves).
        @param actor_name Display name of actor for notifications.
        @param notify_callable Optional async callable(user_id, type, payload) to send notifications.
        @param can_see Optional async callable(user_id) -> bool to filter visible users;
                       if None, all users are assumed visible.
        @param link Notification link (e.g. "/app/events?event=<id>").
        @param label Notification label (e.g. "an event").
        @param fresh Was this target just created? If True and no mentions, return early.

        @return None
        """
        usernames = mentions.extract(content)
        if not usernames and fresh:
            return

        users = await self._tags.users_by_username(community_id, usernames)

        # Build set of valid user ids (exclude actor)
        ids = [u.id for u in users if u.id != actor_id]

        # Apply visibility filter if provided
        if can_see is not None:
            ids = [uid for uid in ids if await can_see(uid)]

        # Filter out blocked users (bidirectional)
        blocked = await self._tags.blocked_with(actor_id, ids)
        ids = [i for i in ids if i not in blocked]

        # Replace tags and get newly tagged user ids
        new_ids = await self._tags.replace_user_tags(
            community_id, target_type, target_id, ids, actor_id
        )

        # Notify newly tagged users (only if notify_callable provided)
        if notify_callable is None:
            return

        for uid in new_ids:
            await notify_callable(
                uid,
                "mention",
                {
                    "actor_name": actor_name,
                    "message": _("%(user)s tagged you in %(where)s")
                    % {"user": actor_name, "where": label},
                    "link": link,
                },
            )
