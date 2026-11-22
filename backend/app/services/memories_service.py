"""
@file memories_service.py
@brief "On this day": a viewer's memories for their local date, and the
       daily 09:00-local reminder.
"""

from __future__ import annotations

import uuid
from calendar import isleap
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import NotFoundError
from app.core.features import require_feature
from app.repositories.community_repo import CommunityRepository
from app.repositories.post_memories_repo import PostMemoriesRepository
from app.repositories.user_repo import UserRepository
from app.services.notification_service import NotificationService

REMINDER_HOUR = 9
"""@brief Local hour at which the reminder fires."""

_RESEND_GUARD = timedelta(hours=20)


def _zone(tz: str | None) -> ZoneInfo:
    """@return The zone, or UTC when unset/invalid."""
    try:
        return ZoneInfo(tz or "UTC")
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return ZoneInfo("UTC")


def local_today(tz: str | None, now: datetime | None = None) -> date:
    """
    @param tz IANA zone name (None/invalid -> UTC).
    @param now Aware instant; defaults to the current time.
    @return The calendar date in that zone.
    """
    return (now or datetime.now(UTC)).astimezone(_zone(tz)).date()


def memory_day(today: date) -> list[tuple[int, int]]:
    """
    @param today Viewer-local date.
    @return ``[(month, day)]`` to match; Feb 29 memories also show on Feb 28 of non-leap years.
    """
    days = [(today.month, today.day)]
    if (today.month, today.day) == (2, 28) and not isleap(today.year):
        days.append((2, 29))
    return days


class MemoriesService:
    """@brief Memories read + reminder job for one community."""

    def __init__(
        self,
        repo: PostMemoriesRepository,
        users: UserRepository,
        communities: CommunityRepository,
        community_id: uuid.UUID,
        notifications: NotificationService | None = None,
    ) -> None:
        self._repo = repo
        self._users = users
        self._communities = communities
        self._cid = community_id
        self._notify = notifications

    async def _gate(self) -> None:
        community = await self._communities.get(self._cid)
        if community is None:
            raise NotFoundError()
        require_feature(community, "on_this_day")

    async def _collect(
        self, viewer_id: uuid.UUID, tz: str | None, now: datetime, limit: int
    ) -> list[dict[str, Any]]:
        today = local_today(tz, now)
        found: list[dict[str, Any]] = []
        for m, d in memory_day(today):
            found += await self._repo.on_this_day(
                self._cid, viewer_id, m, d, today.year, limit, tz=tz or "UTC"
            )
        found.sort(key=lambda p: p["created_at"], reverse=True)
        return found[:limit]

    async def on_this_day(
        self, viewer_id: uuid.UUID, now: datetime | None = None
    ) -> dict[str, Any]:
        """
        @param viewer_id Requesting user.
        @param now Test hook; defaults to the current time.
        @return ``{"items": [post dicts], "years_ago": [int]}`` (parallel lists, newest first).
        @throws AppError FEATURE_DISABLED (404) when the flag is off.
        """
        await self._gate()
        user = await self._users.get_by_id(viewer_id, self._cid)
        if user is None:
            raise NotFoundError()
        now = now or datetime.now(UTC)
        tz = user.timezone
        items = await self._collect(viewer_id, tz, now, 12)
        year = local_today(tz, now).year
        zone = _zone(tz)
        ago = [year - datetime.fromisoformat(p["created_at"]).astimezone(zone).year for p in items]
        return {"items": items, "years_ago": ago}

    async def notify_due(self, now: datetime | None = None) -> int:
        """
        @brief Notify users whose local hour is 9, who have a memory, and were not
               already notified in the last 20 h.
        @return Number of notifications sent.
        """
        if self._notify is None:
            return 0
        community = await self._communities.get(self._cid)
        if community is None:
            return 0
        try:
            require_feature(community, "on_this_day")
        except Exception:
            return 0
        now = now or datetime.now(UTC)
        due = [
            (uid, tz)
            for uid, tz in await self._repo.list_user_tz(self._cid)
            if now.astimezone(_zone(tz)).hour == REMINDER_HOUR
        ]
        if not due:
            return 0
        skip = await self._repo.notified_since(self._cid, [u for u, _ in due], now - _RESEND_GUARD)
        sent = 0
        for uid, tz in due:
            if uid in skip:
                continue
            items = await self._collect(uid, tz, now, 12)
            if not items:
                continue
            await self._notify.notify(
                uid,
                "on_this_day",
                {
                    "message": "You have memories from this day",
                    "count": len(items),
                    "link": "/app?memories=1",
                },
            )
            sent += 1
        return sent
