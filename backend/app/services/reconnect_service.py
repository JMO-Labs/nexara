"""
@file reconnect_service.py
@brief Private "reach out to family" reminders: pick the relative you have
       drifted from, nudge at most weekly, snooze a person for 90 days.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from app.core.exceptions import AppError, NotFoundError
from app.core.features import is_enabled, require_feature
from app.core.i18n import _
from app.repositories.community_repo import CommunityRepository
from app.repositories.reconnect_repo import ReconnectRepository
from app.repositories.user_repo import UserRepository
from app.services.notification_service import NotificationService


class ReconnectService:
    """@brief Pick, send and snooze reconnect reminders."""

    def __init__(
        self,
        repo: ReconnectRepository,
        users: UserRepository,
        communities: CommunityRepository,
        notify: NotificationService,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = repo
        self._users = users
        self._communities = communities
        self._notify = notify
        self._cid = community_id

    async def pick(self, user_id: uuid.UUID, now: datetime) -> uuid.UUID | None:
        """
        @brief The relative to suggest, or None.
        @return Confirmed family member (active, not blocked/memorialized/snoozed)
                with the longest gap beyond the user's days; None if the user opted
                out or already got a reconnect nudge in the last 7 days.
        """
        enabled, days = await self._repo.prefs(user_id, self._cid)
        if not enabled or await self._repo.has_recent_reconnect(user_id, self._cid, now):
            return None
        return await self._repo.stalest_relative(
            user_id, self._cid, now - timedelta(days=days), now
        )

    async def run(self, now: datetime) -> int:
        """
        @brief Daily job: one reminder per eligible user (idempotent via the 7-day cooldown).
        @return Number of notifications sent; 0 when the feature flag is off.
        """
        community = await self._communities.get(self._cid)
        if community is None or not is_enabled(community, "reconnect_nudges"):
            return 0
        sent = 0
        for uid in await self._repo.eligible_users(self._cid, now):
            target = await self.pick(uid, now)
            person = await self._users.get_by_id(target, self._cid) if target else None
            if person is None:
                continue
            await self._repo.record(uid, self._cid, now)
            await self._notify.notify(
                uid,
                "reconnect",
                {
                    "target_id": str(person.id),
                    "target_name": person.display_name,
                    "message": _("It has been a while since you and %(name)s connected.")
                    % {"name": person.display_name},
                    "link": f"/app/chat?dm={person.id}",
                },
            )
            sent += 1
        return sent

    async def snooze(self, user_id: uuid.UUID, target_id: uuid.UUID, now: datetime) -> datetime:
        """
        @brief Mute reminders about ``target_id`` for 90 days.
        @raises AppError FEATURE_DISABLED, VALIDATION_ERROR (self), NotFoundError.
        """
        community = await self._communities.get(self._cid)
        if community is not None:
            require_feature(community, "reconnect_nudges")
        if target_id == user_id:
            raise AppError("VALIDATION_ERROR", _("You cannot snooze yourself"), 422)
        if await self._users.get_by_id(target_id, self._cid) is None:
            raise NotFoundError(_("User not found"))
        return await self._repo.snooze(user_id, target_id, now)
