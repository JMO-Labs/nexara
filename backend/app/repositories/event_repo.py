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
from app.models.user import User
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
        subgroup_id: uuid.UUID | None = None,
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
        @param subgroup_id Optional single subgroup ID to filter events.
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
                and_(Event.visibility == "community", Event.subgroup_id.is_(None)),
                and_(Event.visibility == "private", Event.author_id == viewer_id),
                and_(
                    Event.visibility == "subgroup",
                    Event.subgroup_id.in_(allowed_ids) if allowed_ids else literal(False),
                ),
            )
            stmt = stmt.where(visible)
            stmt = self.apply_block_filter(stmt, viewer_id)

        if subgroup_id is not None:
            stmt = stmt.where(Event.subgroup_id == subgroup_id)

        stmt = stmt.order_by(Event.starts_at.asc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_ical_uid(
        self, *ical_uids: str, subscription_id: uuid.UUID, community_id: uuid.UUID
    ) -> Event | None:
        """
        @brief Find an event imported by one subscription via any of its UIDs.

        Scoped to the subscription and community so a feed can never match
        (and overwrite) native events or events imported by other users.
        Soft-deleted rows are included on purpose: ``ical_uid`` is unique.

        @param ical_uids Candidate UIDs (namespaced first, legacy raw second).
        @param subscription_id Owning subscription.
        @param community_id Tenant scope.
        @return First matching event, or None.
        """
        stmt = (
            select(Event)
            .where(
                Event.ical_uid.in_(ical_uids),
                Event.source_subscription_id == subscription_id,
                Event.community_id == community_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

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
        """@brief List a user's calendar subscriptions + admin-shared subscriptions.

        Returns both:
        1. Subscriptions owned by the user
        2. Subscriptions created by admins with shared_by_admin=True
        """
        stmt = (
            select(CalendarSubscription)
            .where(
                CalendarSubscription.community_id == community_id,
                or_(
                    CalendarSubscription.user_id == user_id,
                    CalendarSubscription.shared_by_admin.is_(True),
                ),
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

    async def update_subscription(self, sub: CalendarSubscription) -> CalendarSubscription:
        """@brief Flush pending changes on a subscription."""
        await self._session.flush()
        await self._session.refresh(sub)
        return sub

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

    async def get_ical_people(
        self, events: list[Event], *, viewer_id: uuid.UUID
    ) -> dict[uuid.UUID, dict[str, Any]]:
        """
        @brief Organizer (author) and attending/maybe RSVPs per event, for iCal.

        Emails are never selected (privacy); attendees blocked by/blocking the
        viewer are excluded.
        @return {event_id: {"organizer": (user_id, name) | None,
                 "attendees": [(user_id, name, status)]}}
        """
        from app.models.moderation import UserBlock

        if not events:
            return {}
        ids = [e.id for e in events]
        out: dict[uuid.UUID, dict[str, Any]] = {e.id: {"attendees": []} for e in events}
        authors = {e.author_id for e in events}
        rows = await self._session.execute(
            select(User.id, User.display_name).where(User.id.in_(authors))
        )
        users = {r[0]: r[1] for r in rows.all()}
        for e in events:
            name = users.get(e.author_id)
            out[e.id]["organizer"] = (e.author_id, name) if name is not None else None
        blocked = select(UserBlock.blocked_id).where(UserBlock.blocker_id == viewer_id)
        blockers = select(UserBlock.blocker_id).where(UserBlock.blocked_id == viewer_id)
        att = await self._session.execute(
            select(EventAttendance.event_id, User.id, User.display_name, EventAttendance.status)
            .join(User, User.id == EventAttendance.user_id)
            .where(
                EventAttendance.event_id.in_(ids),
                EventAttendance.status.in_(["attending", "maybe"]),
                EventAttendance.user_id.notin_(blocked),
                EventAttendance.user_id.notin_(blockers),
            )
        )
        for ev_id, uid, name, status in att.all():
            out[ev_id]["attendees"].append((uid, name, status))
        return out

    async def list_attendees(
        self, event_id: uuid.UUID, statuses: list[str] | None = None
    ) -> list[uuid.UUID]:
        """@brief Return list of user IDs attending an event with given statuses."""
        stmt = select(EventAttendance.user_id).where(EventAttendance.event_id == event_id)
        if statuses:
            stmt = stmt.where(EventAttendance.status.in_(statuses))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def exists_many(
        self,
        event_ids: set[uuid.UUID] | list[uuid.UUID],
    ) -> set[uuid.UUID]:
        """
        @brief Batch-check which event IDs exist (soft-delete aware).

        @param event_ids Set or list of event UUIDs to check.
        @return Set of event IDs that exist (not soft-deleted).
        """
        stmt = select(Event.id).where(Event.id.in_(list(event_ids)))
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def count_subscriptions_for(self, user_id: uuid.UUID) -> int:
        """@brief Count active (non-deleted) subscriptions for a user."""
        stmt = (
            select(func.count())
            .select_from(CalendarSubscription)
            .where(
                CalendarSubscription.user_id == user_id,
            )
        )
        # Apply soft-delete filter if the model has deleted_at
        if hasattr(CalendarSubscription, "deleted_at"):
            stmt = stmt.where(getattr(CalendarSubscription, "deleted_at").is_(None))
        result = await self._session.execute(stmt)
        return result.scalar() or 0
