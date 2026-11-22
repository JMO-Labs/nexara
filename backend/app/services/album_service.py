"""
@file album_service.py
@brief "Share your photos" reminder for event albums (hourly beat, idempotent).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from app.core.features import is_enabled
from app.core.i18n import _
from app.repositories.album_repo import AlbumRepository
from app.repositories.community_repo import CommunityRepository
from app.services.notification_service import NotificationService

WINDOW_START = timedelta(hours=30)
"""@brief Events that ended longer ago than this are no longer reminded."""
WINDOW_END = timedelta(hours=18)
"""@brief Events must have ended at least this long ago."""


class AlbumService:
    """@brief Album reminder logic."""

    def __init__(
        self,
        repo: AlbumRepository,
        community_repo: CommunityRepository,
        notifications: NotificationService,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = repo
        self._communities = community_repo
        self._notify = notifications
        self._community_id = community_id

    async def remind_due(self, now: datetime) -> int:
        """
        @brief Notify "going" RSVPs of events that ended 18-30 h ago, then stamp them.
        @param now Current UTC time.
        @return Number of events reminded.
        """
        community = await self._communities.get(self._community_id)
        if community is None or not is_enabled(community, "event_albums"):
            return 0
        rows = await self._repo.due_for_reminder(now, now - WINDOW_START, now - WINDOW_END)
        rows = [(e, g) for e, g in rows if e.community_id == self._community_id]
        for event, gallery_id in rows:
            for uid in await self._repo.going_user_ids(event.id):
                await self._notify.notify(
                    uid,
                    "album_reminder",
                    {
                        "message": _("Share your photos from %(title)s") % {"title": event.title},
                        "link": f"/app/photos?gallery={gallery_id}",
                        "event_id": str(event.id),
                        "gallery_id": str(gallery_id),
                        "title": event.title,
                    },
                )
        await self._repo.stamp_reminded([e.id for e, _g in rows], now)
        return len(rows)
