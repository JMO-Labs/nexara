"""
@file trip_service.py
@brief Safe-arrival trips: start, extend, arrive, cancel, read and the beat
       sweep that raises one overdue alert and auto-ends stale trips.
       No location is ever stored or sent.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.core.exceptions import AppError, NotFoundError, RateLimitError
from app.core.features import require_feature
from app.core.i18n import _
from app.models.trip import Trip
from app.repositories.community_repo import CommunityRepository
from app.repositories.trip_repo import TripRepository
from app.schemas.trip import TripCreate, TripOut, TripPerson
from app.services.notification_service import NotificationService

MIN_LEAD = timedelta(minutes=10)
MAX_LEAD = timedelta(hours=72)
TRIPS_PER_HOUR = 5


def _invalid(message: str) -> AppError:
    return AppError("VALIDATION_ERROR", message, 422)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


class TripService:
    """@brief Business rules for safe-arrival trips."""

    def __init__(
        self,
        repo: TripRepository,
        community_repo: CommunityRepository,
        notifications: NotificationService,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = repo
        self._communities = community_repo
        self._notify = notifications
        self._community_id = community_id

    async def _require_feature(self) -> None:
        community = await self._communities.get(self._community_id)
        if community is not None:
            require_feature(community, "safe_arrival")

    @staticmethod
    def _check_window(expected_at: datetime, now: datetime) -> datetime:
        expected = _utc(expected_at)
        if expected < now + MIN_LEAD:
            raise _invalid(_("Expected arrival must be at least 10 minutes from now"))
        if expected > now + MAX_LEAD:
            raise _invalid(_("Expected arrival must be within 72 hours"))
        return expected

    async def _tell_watchers(self, trip: Trip, kind: str, message: str) -> None:
        """@brief Notify watchers still eligible right now (re-checked per send)."""
        ids = await self._repo.watcher_ids(trip.id)
        ok = await self._repo.eligible_user_ids(ids, trip.user_id, self._community_id)
        name = (await self._repo.names([trip.user_id])).get(trip.user_id, "")
        for uid in ok:
            await self._notify.notify(
                uid,
                kind,
                {
                    "message": message % {"name": name, "label": trip.label},
                    "link": "/app",
                    "trip_id": str(trip.id),
                    "label": trip.label,
                    "traveler_name": name,
                },
                trip.user_id,
            )

    async def _out(self, trip: Trip, viewer_id: uuid.UUID) -> TripOut:
        ids = await self._repo.watcher_ids(trip.id) if trip.user_id == viewer_id else []
        names = await self._repo.names([trip.user_id, *ids])
        return TripOut(
            id=trip.id,
            label=trip.label,
            expected_at=trip.expected_at,
            arrived_at=trip.arrived_at,
            alerted_at=trip.alerted_at,
            ended_at=trip.ended_at,
            traveler=TripPerson(id=trip.user_id, display_name=names.get(trip.user_id, "")),
            watchers=[TripPerson(id=i, display_name=names.get(i, "")) for i in ids],
        )

    async def start(self, user_id: uuid.UUID, body: TripCreate) -> TripOut:
        """
        @brief Start a trip and tell the watchers.
        @raises AppError 422 bad time/watchers, 409 when a trip is already active.
        """
        await self._require_feature()
        now = datetime.now(UTC)
        # Starting a trip pings every watcher; cap it so it can't be used to spam.
        if (
            await self._repo.count_started_since(
                user_id, self._community_id, now - timedelta(hours=1)
            )
            >= TRIPS_PER_HOUR
        ):
            raise RateLimitError(_("You can start up to 5 trips an hour"))
        expected = self._check_window(body.expected_at, now)
        wanted = list(dict.fromkeys(body.watcher_ids))
        ok = await self._repo.eligible_user_ids(wanted, user_id, self._community_id)
        if set(wanted) - ok:
            raise _invalid(_("One of the chosen watchers cannot be added"))
        trip = await self._repo.create(
            self._community_id, user_id, body.label.strip(), expected, wanted
        )
        if trip is None:
            raise AppError("TRIP_ACTIVE", _("You already have an active trip"), 409)
        await self._tell_watchers(trip, "trip_started", _("%(name)s started a trip: %(label)s"))
        return await self._out(trip, user_id)

    async def _own_active(self, trip_id: uuid.UUID, user_id: uuid.UUID) -> Trip:
        """@brief Lock the traveler's own trip; others and missing get 404, ended 409."""
        trip = await self._repo.get(trip_id, self._community_id, lock=True)
        if trip is None or trip.user_id != user_id:
            raise NotFoundError(_("Trip not found"))
        if trip.arrived_at is not None or trip.ended_at is not None:
            raise AppError("TRIP_ENDED", _("This trip has already ended"), 409)
        return trip

    async def extend(
        self, trip_id: uuid.UUID, user_id: uuid.UUID, expected_at: datetime
    ) -> TripOut:
        """@brief Move the expected time; clears ``alerted_at`` so it can alert again."""
        await self._require_feature()
        trip = await self._own_active(trip_id, user_id)
        trip.expected_at = self._check_window(expected_at, datetime.now(UTC))
        trip.alerted_at = None
        return await self._out(trip, user_id)

    async def arrive(self, trip_id: uuid.UUID, user_id: uuid.UUID) -> TripOut:
        """@brief "Made it": stamp arrival and tell watchers."""
        await self._require_feature()
        trip = await self._own_active(trip_id, user_id)
        trip.arrived_at = datetime.now(UTC)
        await self._tell_watchers(trip, "trip_arrived", _("%(name)s made it: %(label)s"))
        return await self._out(trip, user_id)

    async def cancel(self, trip_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """@brief End the trip silently."""
        await self._require_feature()
        trip = await self._own_active(trip_id, user_id)
        trip.ended_at = datetime.now(UTC)

    async def active(self, user_id: uuid.UUID) -> TripOut | None:
        """@return The viewer's own active trip, if any."""
        await self._require_feature()
        trip = await self._repo.active_for_user(user_id, self._community_id)
        return await self._out(trip, user_id) if trip else None

    async def watching(self, viewer_id: uuid.UUID) -> list[TripOut]:
        """@return Active trips of people the viewer watches."""
        await self._require_feature()
        trips = await self._repo.list_watching(viewer_id, self._community_id)
        return [await self._out(t, viewer_id) for t in trips]

    async def get(self, trip_id: uuid.UUID, viewer_id: uuid.UUID) -> TripOut:
        """@raises NotFoundError unless viewer is the traveler or a watcher."""
        await self._require_feature()
        trip = await self._repo.get(trip_id, self._community_id)
        if trip is None:
            raise NotFoundError(_("Trip not found"))
        if trip.user_id != viewer_id:
            watching = await self._repo.is_watcher(trip.id, viewer_id)
            visible = await self._repo.eligible_user_ids(
                [viewer_id], trip.user_id, self._community_id
            )
            if not (watching and viewer_id in visible):
                raise NotFoundError(_("Trip not found"))
        return await self._out(trip, viewer_id)

    async def sweep(self, now: datetime) -> dict[str, int]:
        """
        @brief Beat entry: one overdue alert per due trip, then auto-end stale ones.
        @return ``{"alerted": n, "ended": n}``.
        """
        alerted = await self._repo.claim_overdue(now)
        for trip in alerted:
            await self._tell_watchers(
                trip, "trip_overdue", _("%(name)s has not arrived yet: %(label)s")
            )
        ended = await self._repo.end_stale(now)
        return {"alerted": len(alerted), "ended": ended}
