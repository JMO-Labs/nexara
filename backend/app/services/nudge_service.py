"""
@file nudge_service.py
@brief Business logic for user-initiated and automated gentle nudges.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AppError, AuthorizationError, NotFoundError, RateLimitError
from app.core.i18n import _
from app.models.user import User
from app.repositories.nudge_repo import NudgeRepository
from app.repositories.user_repo import UserRepository


def _to_dict(n: Any) -> dict[str, Any]:
    return {
        "id": n.id,
        "sender_id": n.sender_id,
        "target_id": n.target_id,
        "nudge_type": n.nudge_type,
        "created_at": n.created_at,
    }


class NudgeService:
    """@brief Send user nudges and run the daily gentle-nudge sweep."""

    def __init__(
        self,
        repo: NudgeRepository,
        user_repo: UserRepository,
        notify: Any,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = repo
        self._users = user_repo
        self._notify = notify
        self._community_id = community_id

    async def send(self, sender: User, target_id: uuid.UUID) -> dict[str, Any]:
        """
        @brief Nudge another user.
        @raises AppError NUDGE_SELF (400), NotFoundError, AuthorizationError (blocked),
                RateLimitError (already nudged within 24h).
        """
        if sender.id == target_id:
            raise AppError("NUDGE_SELF", _("You cannot nudge yourself"), 400)
        if await self._users.get_by_id(target_id, self._community_id) is None:
            raise NotFoundError(_("User not found"))
        if await self._repo.is_blocked(sender.id, target_id, self._community_id):
            raise AuthorizationError(_("You cannot nudge this user"))
        if await self._repo.has_recent_user_nudge(sender.id, target_id, self._community_id):
            raise RateLimitError(_("You can nudge this user once every 24 hours"))
        nudge = await self._repo.create_nudge(
            sender.id, target_id, "user_initiated", self._community_id
        )
        await self._notify.notify(
            target_id,
            "nudge_received",
            {"message": _("%(name)s nudged you!") % {"name": sender.display_name}, "link": "/app"},
            sender.id,
        )
        return _to_dict(nudge)

    async def send_gentle_nudges(self, community_id: uuid.UUID) -> int:
        """
        @brief Notify inactive, opted-in users (idempotent: 7-day cooldown per user).
        @return Number of users nudged.
        """
        ids = await self._repo.find_gentle_candidates(community_id)
        for uid in ids:
            await self._repo.create_nudge(uid, uid, "gentle", community_id)
            await self._notify.notify(
                uid,
                "gentle_nudge",
                {"message": _("We miss you! Come check what's new."), "link": "/app"},
            )
        return len(ids)
