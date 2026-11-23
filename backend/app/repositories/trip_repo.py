"""
@file trip_repo.py
@brief Data access for safe-arrival trips. Every query is community scoped;
       the sweep claims rows with a single UPDATE ... RETURNING (idempotent).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import Boolean, and_, cast, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import Community
from app.models.trip import Trip, TripWatcher
from app.models.user import User
from app.repositories.visibility_preds import not_blocked

OVERDUE_GRACE = timedelta(hours=1)
AUTO_END_AFTER = timedelta(hours=24)
_ACTIVE = (Trip.arrived_at.is_(None), Trip.ended_at.is_(None))


class TripRepository:
    """@brief Persistence for Trip and TripWatcher."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def eligible_user_ids(
        self, ids: list[uuid.UUID], traveler_id: uuid.UUID, community_id: uuid.UUID
    ) -> set[uuid.UUID]:
        """@brief Subset of ``ids`` that may watch: active, same community, not
        memorialized/deleted, not the traveler, no block either way."""
        stmt = select(User.id).where(
            User.id.in_(ids),
            User.id != traveler_id,
            User.community_id == community_id,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            User.memorialized_at.is_(None),
            not_blocked(User.id, traveler_id),
        )
        return set((await self._session.execute(stmt)).scalars())

    async def create(
        self,
        community_id: uuid.UUID,
        user_id: uuid.UUID,
        label: str,
        expected_at: datetime,
        watcher_ids: list[uuid.UUID],
    ) -> Trip | None:
        """@return The trip, or None when the user already has an active one."""
        trip = Trip(
            community_id=community_id, user_id=user_id, label=label, expected_at=expected_at
        )
        try:
            async with self._session.begin_nested():
                self._session.add(trip)
                await self._session.flush()
        except IntegrityError:
            return None
        self._session.add_all([TripWatcher(trip_id=trip.id, user_id=w) for w in watcher_ids])
        await self._session.flush()
        await self._session.refresh(trip)
        return trip

    async def count_started_since(
        self, user_id: uuid.UUID, community_id: uuid.UUID, since: datetime
    ) -> int:
        """@brief Trips this user started since ``since`` (rate limiting)."""
        stmt = select(func.count()).where(
            Trip.user_id == user_id, Trip.community_id == community_id, Trip.created_at >= since
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def get(
        self, trip_id: uuid.UUID, community_id: uuid.UUID, *, lock: bool = False
    ) -> Trip | None:
        """@brief Fetch one trip, optionally ``FOR UPDATE``."""
        stmt = select(Trip).where(Trip.id == trip_id, Trip.community_id == community_id)
        if lock:
            stmt = stmt.with_for_update()
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def active_for_user(self, user_id: uuid.UUID, community_id: uuid.UUID) -> Trip | None:
        """@brief The user's active (not arrived, not ended) trip."""
        stmt = select(Trip).where(
            Trip.user_id == user_id, Trip.community_id == community_id, *_ACTIVE
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_watching(self, viewer_id: uuid.UUID, community_id: uuid.UUID) -> list[Trip]:
        """@brief Active trips the viewer watches, minus blocked travelers."""
        stmt = (
            select(Trip)
            .join(TripWatcher, TripWatcher.trip_id == Trip.id)
            .where(
                TripWatcher.user_id == viewer_id,
                Trip.community_id == community_id,
                not_blocked(Trip.user_id, viewer_id),
                *_ACTIVE,
            )
            .order_by(Trip.expected_at)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def is_watcher(self, trip_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief Whether the user is on the trip's watcher list."""
        stmt = select(TripWatcher.user_id).where(
            TripWatcher.trip_id == trip_id, TripWatcher.user_id == user_id
        )
        return (await self._session.execute(stmt)).first() is not None

    async def watcher_ids(self, trip_id: uuid.UUID) -> list[uuid.UUID]:
        """@brief Raw watcher ids (filter with ``eligible_user_ids`` before use)."""
        stmt = select(TripWatcher.user_id).where(TripWatcher.trip_id == trip_id)
        return list((await self._session.execute(stmt)).scalars())

    async def names(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        """@return display names by user id."""
        if not ids:
            return {}
        rows = await self._session.execute(
            select(User.id, User.display_name).where(User.id.in_(ids))
        )
        return {r[0]: r[1] for r in rows}

    async def claim_overdue(self, now: datetime) -> list[Trip]:
        """@brief Stamp ``alerted_at`` on overdue trips (flag on) and return them."""
        enabled = func.coalesce(cast(Community.features["safe_arrival"].astext, Boolean), True)
        due = (
            select(Trip.id)
            .join(Community, Community.id == Trip.community_id)
            .where(
                and_(*_ACTIVE),
                Trip.alerted_at.is_(None),
                Trip.expected_at + OVERDUE_GRACE < now,
                enabled,
            )
        )
        stmt = (
            update(Trip)
            .where(Trip.id.in_(due.scalar_subquery()), Trip.alerted_at.is_(None))
            .values(alerted_at=now)
            .returning(Trip)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def end_stale(self, now: datetime) -> int:
        """@brief Auto-end trips past expected + 24h. @return rows ended."""
        stmt = (
            update(Trip)
            .where(*_ACTIVE, Trip.expected_at + AUTO_END_AFTER < now)
            .values(ended_at=now)
        )
        return (await self._session.execute(stmt)).rowcount or 0  # type: ignore[attr-defined]
