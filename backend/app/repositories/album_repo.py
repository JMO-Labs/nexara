"""
@file album_repo.py
@brief Queries for event-album reminders and the recap "new albums" section.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventAttendance
from app.models.gallery import Gallery
from app.models.user import User
from app.repositories.visibility_preds import gallery_visible, my_subgroup_ids, not_blocked


class AlbumRepository:
    """@brief Reads/writes for event albums."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def due_for_reminder(
        self, now: datetime, lo: datetime, hi: datetime
    ) -> list[tuple[Event, uuid.UUID]]:
        """
        @param now Unused clock hint kept for symmetry with other beat repos.
        @param lo Earliest event end (inclusive).
        @param hi Latest event end (inclusive).
        @return ``(event, gallery_id)`` for events with an event gallery that ended in
                ``[lo, hi]`` and were never reminded.
        """
        stmt = (
            select(Event, Gallery.id)
            .join(
                Gallery,
                (Gallery.event_id == Event.id) & Gallery.is_event_gallery.is_(True),
            )
            .where(
                Event.ends_at >= lo,
                Event.ends_at <= hi,
                Event.album_reminded_at.is_(None),
                Event.source_removed.is_(False),
            )
        )
        return [(e, g) for e, g in (await self._session.execute(stmt)).all()]

    async def going_user_ids(self, event_id: uuid.UUID) -> list[uuid.UUID]:
        """@return Active users whose RSVP is "attending"."""
        stmt = (
            select(EventAttendance.user_id)
            .join(User, User.id == EventAttendance.user_id)
            .where(
                EventAttendance.event_id == event_id,
                EventAttendance.status == "attending",
                User.deleted_at.is_(None),
            )
        )
        return list((await self._session.execute(stmt)).scalars())

    async def stamp_reminded(self, event_ids: list[uuid.UUID], now: datetime) -> None:
        """@brief Record ``album_reminded_at`` so the job never repeats."""
        if event_ids:
            await self._session.execute(
                update(Event).where(Event.id.in_(event_ids)).values(album_reminded_at=now)
            )

    async def new_event_galleries(
        self, community_id: uuid.UUID, viewer_id: uuid.UUID, since: datetime
    ) -> list[Gallery]:
        """@return Event galleries created since ``since`` with >=1 item the viewer may open."""
        stmt = (
            select(Gallery)
            .where(
                gallery_visible(viewer_id, my_subgroup_ids(viewer_id), community_id),
                Gallery.is_event_gallery.is_(True),
                Gallery.item_count >= 1,
                Gallery.created_at >= since,
                not_blocked(Gallery.owner_id, viewer_id),
            )
            .order_by(Gallery.created_at.desc())
            .limit(20)
        )
        return list((await self._session.execute(stmt)).scalars())
