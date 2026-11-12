"""
@file birthday_service.py
@brief Birthday reminder business logic with privacy filtering.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import structlog

from app.repositories.birthday_repo import BirthdayRepository
from app.repositories.post_repo import PostRepository

logger = structlog.get_logger(__name__)


class BirthdayService:
    """
    @brief Notifies community members of today's birthdays.

    @param repo BirthdayRepository.
    @param notification_service NotificationService scoped to the community.
    @param post_repo PostRepository (used only when auto_post is enabled).
    @param community_id Community scope.
    @param auto_post Create a feed announcement for community-visible birthdays.
    """

    def __init__(
        self,
        repo: BirthdayRepository,
        notification_service: Any,
        post_repo: PostRepository,
        community_id: uuid.UUID,
        auto_post: bool = False,
    ) -> None:
        self._repo = repo
        self._notif = notification_service
        self._posts = post_repo
        self._community_id = community_id
        self._auto_post = auto_post

    async def send_reminders(self, today: date) -> int:
        """
        @brief Notify eligible members about birthdays on ``today``.

        'nobody' skips entirely; 'admin_only' notifies admins; anything else
        ('community') notifies all members. The birthday user is never notified.
        @return Number of notifications sent.
        """
        users = await self._repo.list_birthday_users(self._community_id, today.month, today.day)
        sent = 0
        for user, show_to in users:
            if show_to == "nobody":
                continue
            if show_to == "admin_only":
                recipients = await self._repo.list_admin_ids(self._community_id)
            else:
                recipients = await self._repo.list_member_ids(self._community_id)
            message = f"{user.display_name}'s birthday is today!"
            for rid in recipients:
                if rid == user.id:
                    continue
                await self._notif.notify(
                    user_id=rid,
                    type="birthday_reminder",
                    payload={"message": message, "user_id": str(user.id)},
                    actor_id=user.id,
                )
                sent += 1
            if self._auto_post and show_to == "community":
                await self._posts.create_post(
                    author_id=user.id,
                    content=f"Happy birthday, {user.display_name}!",
                    community_id=self._community_id,
                )
        logger.info("birthday_reminders_sent", community_id=str(self._community_id), sent=sent)
        return sent
