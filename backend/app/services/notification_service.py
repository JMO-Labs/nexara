"""
@file notification_service.py
@brief Business logic for in-app and email notifications.

Respects user notification preferences and mutes.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from app.core.i18n import _
from app.models.notification import Notification
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.notification import NotificationList, NotificationResponse, UnreadCountResponse

logger = structlog.get_logger(__name__)

NOTIFICATION_TYPES = (
    "mention",
    "comment",
    "reaction",
    "new_post",
    "system",
    "invite_accepted",
)
"""@brief Supported notification types for preference lookup."""

PREF_MAP = {
    "mention": ("notif_mention_inapp", "notif_mention_email"),
    "comment": ("notif_comment_inapp", "notif_comment_email"),
    "reaction": ("notif_reaction_inapp", "notif_reaction_email"),
    "new_post": ("notif_new_post_inapp", "notif_new_post_email"),
    "system": ("notif_system_inapp", "notif_system_email"),
    "invite_accepted": ("notif_invite_accepted_inapp", "notif_invite_accepted_email"),
}


class NotificationService:
    """
    @brief Service layer for notification creation and delivery.

    @param notification_repo NotificationRepository instance.
    @param settings_repo SettingsRepository instance.
    @param pubsub_publisher Optional coroutine (user_id, message) -> int.
    @param community_id Community scope.
    """

    def __init__(
        self,
        notification_repo: NotificationRepository,
        settings_repo: SettingsRepository,
        community_id: uuid.UUID,
        *,
        pubsub_publisher: Callable[[uuid.UUID, dict[str, Any]], Awaitable[int]] | None = None,
    ) -> None:
        self._notification_repo = notification_repo
        self._settings_repo = settings_repo
        self._community_id = community_id
        self._pubsub = pubsub_publisher

    async def notify(
        self,
        user_id: uuid.UUID,
        type: str,
        payload: dict[str, Any],
        actor_id: uuid.UUID | None = None,
    ) -> Notification | None:
        """
        @brief Create and deliver a notification based on user preferences.

        If in-app enabled: create DB record and publish SSE event.
        If email enabled and not mute_all_email: enqueue Celery task.

        @param user_id Recipient user UUID.
        @param type Notification type (mention, comment, etc.).
        @param payload JSON payload (message, link, etc.).
        @param actor_id Optional actor UUID.
        @return Created Notification or None if in-app disabled.
        """
        if type not in PREF_MAP:
            logger.warning("notification_unknown_type", type=type)
            return None

        inapp_key, email_key = PREF_MAP[type]
        settings = await self._settings_repo.get_or_create(user_id, self._community_id)
        inapp_enabled = getattr(settings, inapp_key, True)
        email_enabled = getattr(settings, email_key, False)
        mute_email = getattr(settings, "mute_all_email", False)

        notification: Notification | None = None
        if inapp_enabled:
            notification = await self._notification_repo.create(
                user_id, type, payload, self._community_id
            )
            if self._pubsub:
                msg = {
                    "type": "notification",
                    "payload": {
                        "id": str(notification.id),
                        "type": type,
                        "payload": payload,
                        "created_at": notification.created_at.isoformat(),
                    },
                }
                await self._pubsub(user_id, msg)

        if email_enabled and not mute_email:
            from app.tasks.notification_tasks import send_email_notification

            send_email_notification.delay(
                str(user_id),
                type,
                {**payload, "actor_id": str(actor_id) if actor_id else None},
            )

        return notification

    @staticmethod
    def detect_mentions(content: str) -> list[str]:
        """
        @brief Extract @username mentions from text, excluding code blocks.

        Skips mentions inside backtick-wrapped code blocks.

        @param content Plain text or markdown content.
        @return List of unique usernames (without @).
        """
        in_code = False
        result: list[str] = []
        for part in re.split(r"(`+)", content):
            if part == "`":
                in_code = not in_code
                continue
            if in_code or part.startswith("`"):
                continue
            for m in re.finditer(r"@([a-zA-Z0-9_-]+)", part):
                result.append(m.group(1))
        return list(dict.fromkeys(result))

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 20,
    ) -> NotificationList:
        """@brief List notifications for a user with pagination."""
        items, next_cursor = await self._notification_repo.list_for_user(
            user_id, cursor=cursor, limit=limit
        )
        return NotificationList(
            items=[NotificationResponse.model_validate(n) for n in items],
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
        )

    async def get_unread_count(self, user_id: uuid.UUID) -> UnreadCountResponse:
        """@brief Return unread count for badge display."""
        count = await self._notification_repo.get_unread_count(user_id)
        return UnreadCountResponse(count=count)

    async def mark_read(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """@brief Mark a notification as read."""
        return await self._notification_repo.mark_read(notification_id, user_id)

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        """@brief Mark all notifications as read for a user."""
        return await self._notification_repo.mark_all_read(user_id)
