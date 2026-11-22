"""
@file ride_service.py
@brief Event rides: offers, requests, seat joins (row-locked), answers and
       cancellation. Every entry point checks the ``rides`` feature and that
       the viewer can see the event (otherwise 404).
"""

from __future__ import annotations

import uuid

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.features import require_feature
from app.core.i18n import _
from app.models.event import Event
from app.models.event_ride import EventRide
from app.repositories.community_repo import CommunityRepository
from app.repositories.event_repo import EventRepository
from app.repositories.ride_repo import RideRepository
from app.schemas.ride import RideCreate, RideOut, RidePassengerOut
from app.services.event_service import EventService
from app.services.notification_service import NotificationService


def _conflict(code: str, message: str) -> AppError:
    return AppError(code, message, 409)


class RideService:
    """@brief Business rules for event rides."""

    def __init__(
        self,
        repo: RideRepository,
        events: EventRepository,
        event_service: EventService,
        community_repo: CommunityRepository,
        notifications: NotificationService,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = repo
        self._events = events
        self._event_service = event_service
        self._communities = community_repo
        self._notify = notifications
        self._community_id = community_id

    # ── guards ────────────────────────────────────────────────────────

    async def _require_feature(self) -> None:
        community = await self._communities.get(self._community_id)
        if community is not None:
            require_feature(community, "rides")

    async def _event(self, event_id: uuid.UUID, viewer_id: uuid.UUID) -> Event:
        """@raises NotFoundError when missing or not viewable."""
        event = await self._events.get_by_id(event_id, community_id=self._community_id)
        if event is None or not await self._event_service._can_view(event, viewer_id):
            raise NotFoundError(_("Event not found"))
        return event

    async def _ride(
        self, ride_id: uuid.UUID, viewer_id: uuid.UUID, *, lock: bool = False
    ) -> tuple[EventRide, Event]:
        """@brief Load a ride whose event and author the viewer may see (else 404)."""
        ride = await self._repo.get(ride_id, self._community_id, lock=lock)
        if ride is None:
            raise NotFoundError(_("Ride not found"))
        event = await self._event(ride.event_id, viewer_id)
        if ride.user_id != viewer_id and await self._repo.blocked_with(viewer_id, [ride.user_id]):
            raise NotFoundError(_("Ride not found"))
        return ride, event

    async def _notify_users(
        self,
        event: Event,
        ride: EventRide,
        action: str,
        message: str,
        recipients: list[uuid.UUID],
        actor_id: uuid.UUID,
    ) -> None:
        """@brief Notify each recipient who is not blocked with the actor and can see the event."""
        skip = await self._repo.blocked_with(actor_id, recipients)
        for uid in dict.fromkeys(recipients):
            if uid == actor_id or uid in skip:
                continue
            if not await self._event_service._can_view(event, uid):
                continue
            await self._notify.notify(
                uid,
                "ride_update",
                {
                    "message": message,
                    "link": f"/app/events/{event.id}",
                    "actor_id": str(actor_id),
                    "ride_id": str(ride.id),
                    "event_id": str(event.id),
                    "event_title": event.title,
                    "action": action,
                },
                actor_id,
            )

    async def _name(self, user_id: uuid.UUID) -> str:
        return (await self._repo.names([user_id])).get(user_id, "")

    # ── reads ─────────────────────────────────────────────────────────

    async def _build(self, rides: list[EventRide], viewer_id: uuid.UUID) -> list[RideOut]:
        rows = await self._repo.passengers_for([r.id for r in rides])
        ids = list({r.user_id for r in rides} | {p.user_id for p in rows})
        hidden = await self._repo.blocked_with(viewer_id, ids)
        names = await self._repo.names(ids)
        out: list[RideOut] = []
        for r in rides:
            mine = [p for p in rows if p.ride_id == r.id]
            out.append(
                RideOut(
                    id=r.id,
                    event_id=r.event_id,
                    kind=r.kind,
                    user_id=r.user_id,
                    driver_name=names.get(r.user_id, ""),
                    seats=r.seats,
                    seats_left=max(r.seats - len(mine), 0) if r.kind == "offer" else 0,
                    origin=r.origin,
                    depart_at=r.depart_at,
                    note=r.note,
                    passengers=[
                        RidePassengerOut(user_id=p.user_id, display_name=names.get(p.user_id, ""))
                        for p in mine
                        if p.user_id not in hidden
                    ],
                    joined=any(p.user_id == viewer_id for p in mine),
                    created_at=r.created_at,
                )
            )
        return out

    async def list_for_event(self, event_id: uuid.UUID, viewer_id: uuid.UUID) -> list[RideOut]:
        """@return Visible offers and requests for the event."""
        await self._require_feature()
        await self._event(event_id, viewer_id)
        rides = await self._repo.list_for_event(event_id, self._community_id, viewer_id)
        return await self._build(rides, viewer_id)

    # ── writes ────────────────────────────────────────────────────────

    async def _create(
        self, kind: str, event_id: uuid.UUID, user_id: uuid.UUID, body: RideCreate
    ) -> RideOut:
        await self._require_feature()
        await self._event(event_id, user_id)
        if await self._repo.memorialized(user_id):
            raise AuthorizationError(_("This account cannot take part in rides"))
        await self._repo.lock_rider(event_id, user_id)
        if kind == "offer" and await self._repo.riding(event_id, user_id):
            raise _conflict("ALREADY_RIDING", _("You already have a seat for this event"))
        ride = await self._repo.create(
            self._community_id,
            event_id,
            kind=kind,
            user_id=user_id,
            seats=body.seats,
            origin=body.origin.strip(),
            depart_at=body.depart_at,
            note=body.note.strip(),
        )
        return (await self._build([ride], user_id))[0]

    async def offer(self, event_id: uuid.UUID, user_id: uuid.UUID, body: RideCreate) -> RideOut:
        """@brief Offer seats to an event. @raises AppError ALREADY_RIDING (409)."""
        return await self._create("offer", event_id, user_id, body)

    async def request(self, event_id: uuid.UUID, user_id: uuid.UUID, body: RideCreate) -> RideOut:
        """@brief Ask for a ride to an event."""
        return await self._create("request", event_id, user_id, body)

    async def _seat(self, offer: EventRide, user_id: uuid.UUID) -> None:
        """@brief Take a seat on a locked offer. @raises AppError RIDE_FULL / ALREADY_RIDING."""
        await self._repo.lock_rider(offer.event_id, user_id)
        if await self._repo.riding(offer.event_id, user_id):
            raise _conflict("ALREADY_RIDING", _("You already have a seat for this event"))
        if len(await self._repo.passenger_ids(offer.id)) >= offer.seats:
            raise _conflict("RIDE_FULL", _("This ride is full"))
        await self._repo.add_passenger(offer.id, user_id)

    async def join(self, ride_id: uuid.UUID, user_id: uuid.UUID) -> RideOut:
        """
        @brief Take a seat (locks the ride row so the last seat cannot be double-booked).
        @raises AppError RIDE_FULL, ALREADY_RIDING (409); 422 for own/request rides.
        """
        await self._require_feature()
        ride, event = await self._ride(ride_id, user_id, lock=True)
        if ride.kind != "offer":
            raise AppError("VALIDATION_ERROR", _("Only offers can be joined"), 422)
        if ride.user_id == user_id:
            raise AppError("VALIDATION_ERROR", _("You cannot join your own ride"), 422)
        if await self._repo.memorialized(user_id):
            raise AuthorizationError(_("This account cannot take part in rides"))
        await self._seat(ride, user_id)
        name = await self._name(user_id)
        await self._notify_users(
            event, ride, "joined", _("%(name)s joined your ride") % {"name": name},
            [ride.user_id], user_id,
        )  # fmt: skip
        return (await self._build([ride], user_id))[0]

    async def leave(self, ride_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """@brief Give up a seat; notifies the driver."""
        await self._require_feature()
        ride, event = await self._ride(ride_id, user_id, lock=True)
        if not await self._repo.remove_passenger(ride.id, user_id):
            raise NotFoundError(_("You are not on this ride"))
        name = await self._name(user_id)
        await self._notify_users(
            event, ride, "left", _("%(name)s left your ride") % {"name": name},
            [ride.user_id], user_id,
        )  # fmt: skip

    async def answer_request(
        self, request_id: uuid.UUID, offer_id: uuid.UUID, driver_id: uuid.UUID
    ) -> RideOut:
        """
        @brief Driver takes the requester onto one of their offers and closes the request.
        @raises AppError RIDE_FULL / ALREADY_RIDING (409), 422 on mismatched rides.
        """
        await self._require_feature()
        offer, event = await self._ride(offer_id, driver_id, lock=True)
        req, _event = await self._ride(request_id, driver_id)
        if offer.kind != "offer" or offer.user_id != driver_id:
            raise AuthorizationError(_("You can only answer with your own offer"))
        if req.kind != "request" or req.event_id != offer.event_id or req.user_id == driver_id:
            raise AppError("VALIDATION_ERROR", _("That request cannot be answered"), 422)
        if await self._repo.memorialized(req.user_id):
            raise AppError("VALIDATION_ERROR", _("That request cannot be answered"), 422)
        await self._seat(offer, req.user_id)
        await self._repo.soft_delete(req)
        name = await self._name(driver_id)
        await self._notify_users(
            event, offer, "answered", _("%(name)s can give you a ride") % {"name": name},
            [req.user_id], driver_id,
        )  # fmt: skip
        return (await self._build([offer], driver_id))[0]

    async def cancel(self, ride_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """@brief Owner cancels an offer or request; passengers are notified."""
        await self._require_feature()
        ride, event = await self._ride(ride_id, user_id, lock=True)
        if ride.user_id != user_id:
            raise AuthorizationError(_("Only the owner can cancel a ride"))
        passengers = await self._repo.passenger_ids(ride.id)
        await self._repo.remove_all_passengers(ride.id)
        await self._repo.soft_delete(ride)
        name = await self._name(user_id)
        await self._notify_users(
            event, ride, "cancelled", _("%(name)s cancelled their ride") % {"name": name},
            passengers, user_id,
        )  # fmt: skip


__all__ = ["RideService"]
