"""
@file event_repo.py
@brief Repository for events, RSVPs, and calendar subscriptions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, delete, func, literal, or_, select

from app.models.event import CalendarSubscription, Event, EventAttendance
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    """@brief Async repo for event CRUD with RSVP and subscription helpers."""

    model = Event

    async def list_in_range(
        self,
        community_id: uuid.UUID,
        start: datetime,
        end: datetime,
        *,
        viewer_id: uuid.UUID | None = None,
        subgroup_ids: list[uuid.UUID] | None = None,
    ) -> list[Event]:
        """
        @brief List events overlapping ``[start, end]``.

        Includes recurring master events whose ``starts_at`` may be earlier
        than ``start`` so the service layer can expand occurrences.

        @param community_id Community scope.
        @param start Window start (UTC).
        @param end Window end (UTC).
        @param viewer_id Optional viewer for block filter + visibility scoping.
        @param subgroup_ids Subgroup IDs the viewer belongs to (for subgroup events).
        @return Event rows.
        """
        stmt = select(Event).where(Event.community_id == community_id)

        # Recurring masters: include any whose ends_at is in the future.
        recur = and_(Event.recurrence_rule.isnot(None), Event.ends_at >= start)
        non_recur = and_(
            Event.recurrence_rule.is_(None),
            Event.starts_at <= end,
            Event.ends_at >= start,
        )
        stmt = stmt.where(or_(recur, non_recur))

        if viewer_id is not None:
            allowed_ids = subgroup_ids or []
            visible = or_(
                Event.visibility == "community",
                and_(Event.visibility == "private", Event.author_id == viewer_id),
                and_(
                    Event.visibility == "subgroup",
                    Event.subgroup_id.in_(allowed_ids) if allowed_ids else literal(False),
                ),
            )
            stmt = stmt.where(visible)
            stmt = self.apply_block_filter(stmt, viewer_id)

        stmt = stmt.order_by(Event.starts_at.asc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_ical_uid(self, ical_uid: str) -> Event | None:
        """@brief Look up an event by its iCal UID (used for sync upserts)."""
        stmt = select(Event).where(Event.ical_uid == ical_uid)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_attendance(
        self, event_id: uuid.UUID, user_id: uuid.UUID
    ) -> EventAttendance | None:
        """@brief Fetch a user's RSVP for an event."""
        stmt = select(EventAttendance).where(
            EventAttendance.event_id == event_id,
            EventAttendance.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_attendance(self, event_id: uuid.UUID) -> list[EventAttendance]:
        """@brief List all RSVP records for an event."""
        stmt = select(EventAttendance).where(EventAttendance.event_id == event_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_attendance(
        self,
        event_id: uuid.UUID,
        user_id: uuid.UUID,
        community_id: uuid.UUID,
        status: str,
        note: str | None,
    ) -> EventAttendance:
        """@brief Insert or update a user's RSVP for an event."""
        existing = await self.get_attendance(event_id, user_id)
        if existing is not None:
            existing.status = status
            existing.note = note
            existing.responded_at = datetime.now(UTC)
            await self._session.flush()
            await self._session.refresh(existing)
            return existing

        att = EventAttendance(
            event_id=event_id,
            user_id=user_id,
            community_id=community_id,
            status=status,
            note=note,
        )
        self._session.add(att)
        await self._session.flush()
        await self._session.refresh(att)
        return att

    async def remove_attendance(self, event_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """@brief Remove a user's RSVP for an event."""
        stmt = delete(EventAttendance).where(
            EventAttendance.event_id == event_id,
            EventAttendance.user_id == user_id,
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def rsvp_counts(self, event_id: uuid.UUID) -> dict[str, int]:
        """@brief Aggregate RSVP counts grouped by ``status``."""
        stmt = (
            select(EventAttendance.status, func.count().label("cnt"))
            .where(EventAttendance.event_id == event_id)
            .group_by(EventAttendance.status)
        )
        result = await self._session.execute(stmt)
        return {row.status: row.cnt for row in result.all()}

    async def list_upcoming_for_reminders(
        self,
        window_start: datetime,
        window_end: datetime,
    ) -> list[Event]:
        """@brief List non-recurring events starting inside the reminder window."""
        stmt = select(Event).where(
            Event.recurrence_rule.is_(None),
            Event.starts_at >= window_start,
            Event.starts_at <= window_end,
            Event.source_removed.is_(False),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_with_offset_in_range(
        self,
        offset_minutes: int,
        start: datetime,
        end: datetime,
    ) -> list[Event]:
        """
        @brief List events with a specific reminder offset.

        Filters events whose reminder_offsets_minutes contains offset
        and whose starts_at falls in [start, end].

        @param offset_minutes The reminder offset to filter by (15, 60, or 1440).
        @param start Window start (UTC).
        @param end Window end (UTC).
        @return Matching Event rows.
        """
        stmt = select(Event).where(
            Event.reminder_offsets_minutes.contains([offset_minutes]),  # @> operator
            Event.starts_at >= start,
            Event.starts_at <= end,
            Event.source_removed.is_(False),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_subscriptions(
        self, community_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[CalendarSubscription]:
        """@brief List a user's calendar subscriptions."""
        stmt = (
            select(CalendarSubscription)
            .where(
                CalendarSubscription.community_id == community_id,
                CalendarSubscription.user_id == user_id,
            )
            .order_by(CalendarSubscription.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_subscription(self, sub: CalendarSubscription) -> CalendarSubscription:
        """@brief Persist a new calendar subscription."""
        self._session.add(sub)
        await self._session.flush()
        await self._session.refresh(sub)
        return sub

    async def get_subscription(
        self, sub_id: uuid.UUID, *, user_id: uuid.UUID | None = None
    ) -> CalendarSubscription | None:
        """@brief Fetch a calendar subscription, optionally scoped to a user."""
        stmt = select(CalendarSubscription).where(CalendarSubscription.id == sub_id)
        if user_id is not None:
            stmt = stmt.where(CalendarSubscription.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_subscription(self, sub_id: uuid.UUID) -> None:
        """@brief Hard-delete a calendar subscription."""
        stmt = delete(CalendarSubscription).where(CalendarSubscription.id == sub_id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def list_subscriptions_due(self, now: datetime, interval: timedelta) -> list[Any]:
        """@brief Return enabled subscriptions whose last sync is older than interval."""
        cutoff = now - interval
        stmt = select(CalendarSubscription).where(
            CalendarSubscription.sync_enabled.is_(True),
            or_(
                CalendarSubscription.last_synced_at.is_(None),
                CalendarSubscription.last_synced_at < cutoff,
            ),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_ended_in_window(self, start: datetime, end: datetime) -> list[Event]:
        """@brief List events that ended between start and end (UTC)."""
        stmt = select(Event).where(
            Event.ends_at >= start,
            Event.ends_at <= end,
            Event.source_removed.is_(False),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_attendees(
        self, event_id: uuid.UUID, statuses: list[str] | None = None
    ) -> list[uuid.UUID]:
        """@brief Return list of user IDs attending an event with given statuses."""
        stmt = select(EventAttendance.user_id).where(EventAttendance.event_id == event_id)
        if statuses:
            stmt = stmt.where(EventAttendance.status.in_(statuses))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
