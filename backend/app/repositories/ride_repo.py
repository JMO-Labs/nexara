"""
@file ride_repo.py
@brief Data access for event rides: viewer-scoped listing (block-aware),
       row-locked seat accounting and passenger management.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_ride import EventRide, RidePassenger
from app.models.moderation import UserBlock
from app.models.user import User
from app.repositories.visibility_preds import not_blocked


class RideRepository:
    """@brief Async repository for EventRide / RidePassenger."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, community_id: uuid.UUID, event_id: uuid.UUID, **values: Any
    ) -> EventRide:
        """@return The persisted ride."""
        ride = EventRide(community_id=community_id, event_id=event_id, **values)
        self._session.add(ride)
        await self._session.flush()
        await self._session.refresh(ride)
        return ride

    async def get(
        self, ride_id: uuid.UUID, community_id: uuid.UUID, *, lock: bool = False
    ) -> EventRide | None:
        """@param lock Take ``SELECT ... FOR UPDATE`` on the row (seat accounting)."""
        stmt = select(EventRide).where(
            EventRide.id == ride_id,
            EventRide.community_id == community_id,
            EventRide.deleted_at.is_(None),
        )
        if lock:
            stmt = stmt.with_for_update()
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_event(
        self, event_id: uuid.UUID, community_id: uuid.UUID, viewer_id: uuid.UUID
    ) -> list[EventRide]:
        """@brief Live rides for the event, minus authors in a block relation with the viewer."""
        stmt = (
            select(EventRide)
            .where(
                EventRide.event_id == event_id,
                EventRide.community_id == community_id,
                EventRide.deleted_at.is_(None),
                not_blocked(EventRide.user_id, viewer_id),
            )
            .order_by(EventRide.depart_at.asc().nulls_last(), EventRide.created_at.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def lock_rider(self, event_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """@brief Transaction-scoped advisory lock serialising one user's seat changes per event."""
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"),
            {"k": f"ride:{event_id}:{user_id}"},
        )

    async def riding(self, event_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief True if the user holds a seat on a live ride of this event."""
        stmt = (
            select(RidePassenger.ride_id)
            .join(EventRide, EventRide.id == RidePassenger.ride_id)
            .where(
                EventRide.event_id == event_id,
                EventRide.deleted_at.is_(None),
                RidePassenger.user_id == user_id,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None

    async def passenger_ids(self, ride_id: uuid.UUID) -> list[uuid.UUID]:
        """@return All passenger ids of the ride (unfiltered; seat accounting)."""
        stmt = select(RidePassenger.user_id).where(RidePassenger.ride_id == ride_id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def passengers_for(self, ride_ids: list[uuid.UUID]) -> list[RidePassenger]:
        """@return Passenger rows for the rides, oldest first."""
        if not ride_ids:
            return []
        stmt = (
            select(RidePassenger)
            .where(RidePassenger.ride_id.in_(ride_ids))
            .order_by(RidePassenger.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def add_passenger(self, ride_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """@brief Seat the user on the ride."""
        self._session.add(RidePassenger(ride_id=ride_id, user_id=user_id))
        await self._session.flush()

    async def remove_passenger(self, ride_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@return True if a seat was released."""
        res = await self._session.execute(
            delete(RidePassenger).where(
                RidePassenger.ride_id == ride_id, RidePassenger.user_id == user_id
            )
        )
        return bool(res.rowcount)  # type: ignore[attr-defined]

    async def remove_all_passengers(self, ride_id: uuid.UUID) -> None:
        """@brief Release every seat on the ride."""
        await self._session.execute(delete(RidePassenger).where(RidePassenger.ride_id == ride_id))

    async def soft_delete(self, ride: EventRide) -> None:
        """@brief Mark the ride deleted (cancelled / answered)."""
        ride.deleted_at = datetime.now(UTC)
        await self._session.flush()

    async def names(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        """@return ``{user_id: display_name}``."""
        if not user_ids:
            return {}
        stmt = select(User.id, User.display_name).where(User.id.in_(user_ids))
        return {r[0]: r[1] for r in (await self._session.execute(stmt)).all()}

    async def memorialized(self, user_id: uuid.UUID) -> bool:
        """@return True if the account is memorialized."""
        stmt = select(User.memorialized_at).where(User.id == user_id)
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def blocked_with(self, viewer_id: uuid.UUID, user_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        """@return Subset of ``user_ids`` in a block relation (either way) with the viewer."""
        if not user_ids:
            return set()
        stmt = select(UserBlock.blocked_id, UserBlock.blocker_id).where(
            ((UserBlock.blocker_id == viewer_id) & UserBlock.blocked_id.in_(user_ids))
            | ((UserBlock.blocked_id == viewer_id) & UserBlock.blocker_id.in_(user_ids))
        )
        out: set[uuid.UUID] = set()
        for blocked, blocker in (await self._session.execute(stmt)).all():
            out.add(blocked if blocker == viewer_id else blocker)
        return out
