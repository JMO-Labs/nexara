"""
@file album_repo.py
@brief Queries for event-album reminders and the recap "new albums" section.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, exists, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventAttendance
from app.models.gallery import Gallery
from app.models.moderation import UserBlock
from app.models.subgroup import SubgroupMember
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
        """
        @return Active "attending" users who can still see the event right now:
                group members for group events, the author for private ones,
                and never anyone in a block relation with the author.
        """
        member = exists().where(
            SubgroupMember.subgroup_id == Event.subgroup_id,
            SubgroupMember.user_id == User.id,
        )
        blocked = exists().where(
            or_(
                and_(UserBlock.blocker_id == User.id, UserBlock.blocked_id == Event.author_id),
                and_(UserBlock.blocker_id == Event.author_id, UserBlock.blocked_id == User.id),
            )
        )
        stmt = (
            select(EventAttendance.user_id)
            .join(User, User.id == EventAttendance.user_id)
            .join(Event, Event.id == EventAttendance.event_id)
            .where(
                EventAttendance.event_id == event_id,
                EventAttendance.status == "attending",
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                or_(
                    and_(Event.visibility == "private", User.id == Event.author_id),
                    and_(
                        Event.visibility != "private",
                        or_(Event.subgroup_id.is_(None), member),
                    ),
                ),
                ~blocked,
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
