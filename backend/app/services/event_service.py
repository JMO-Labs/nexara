"""
@file event_service.py
@brief Event business logic — CRUD, RSVP, contributions, RRULE expansion, iCal.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from dateutil.rrule import rrulestr
from icalendar import Calendar as ICalCalendar
from icalendar import Event as ICalEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.event import CalendarSubscription, Event
from app.models.subgroup import SubgroupMember
from app.repositories.event_repo import EventRepository
from app.schemas.event import (
    CalendarSubscriptionCreate,
    CalendarSubscriptionResponse,
    ContributionClaim,
    ContributionSlot,
    EventCreate,
    EventList,
    EventOccurrence,
    EventResponse,
    EventUpdate,
    RSVPRequest,
    RSVPResponse,
)

logger = structlog.get_logger(__name__)

DEFAULT_RSVP_LABELS: dict[str, str] = {
    "attending": "Attending",
    "maybe": "Maybe",
    "declined": "Declined",
}

# Maximum number of recurrence occurrences expanded per query window.
MAX_OCCURRENCES = 200


class EventService:
    """@brief Service layer for events, RSVPs, and calendar subscriptions."""

    def __init__(
        self,
        event_repo: EventRepository,
        community_id: uuid.UUID,
        session: AsyncSession,
        *,
        notification_service: Any | None = None,
    ) -> None:
        self._repo = event_repo
        self._community_id = community_id
        self._session = session
        self._notifications = notification_service

    # ── Internal helpers ──────────────────────────────────────────────

    async def _user_subgroup_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """Direct memberships expanded with descendants (parent → child cascade)."""
        from app.repositories.subgroup_repo import expand_with_descendants

        stmt = select(SubgroupMember.subgroup_id).where(SubgroupMember.user_id == user_id)
        result = await self._session.execute(stmt)
        direct = list(result.scalars().all())
        return await expand_with_descendants(self._session, direct)

    async def _can_view(self, event: Event, user_id: uuid.UUID) -> bool:
        if event.visibility == "community":
            return True
        if event.visibility == "private":
            return event.author_id == user_id
        if event.visibility == "subgroup":
            if event.subgroup_id is None:
                return False
            ids = await self._user_subgroup_ids(user_id)
            return event.subgroup_id in ids
        return False

    def _slots_to_dicts(self, slots: list[ContributionSlot]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for slot in slots:
            out.append(
                {
                    "id": str(slot.id or uuid.uuid4()),
                    "title": slot.title,
                    "quantity_needed": slot.quantity_needed,
                    "quantity_claimed": slot.quantity_claimed,
                    "claimed_by": [str(uid) for uid in slot.claimed_by],
                }
            )
        return out

    def _slots_from_db(self, raw: list[dict[str, Any]] | None) -> list[ContributionSlot]:
        if not raw:
            return []
        out: list[ContributionSlot] = []
        for item in raw:
            try:
                out.append(
                    ContributionSlot(
                        id=uuid.UUID(item["id"]) if "id" in item else None,
                        title=item.get("title", ""),
                        quantity_needed=int(item.get("quantity_needed", 1)),
                        quantity_claimed=int(item.get("quantity_claimed", 0)),
                        claimed_by=[uuid.UUID(s) for s in item.get("claimed_by", [])],
                    )
                )
            except (ValueError, KeyError, TypeError):
                continue
        return out

    async def _build_response(
        self, event: Event, *, user_id: uuid.UUID | None = None
    ) -> EventResponse:
        rsvp_counts = await self._repo.rsvp_counts(event.id)
        user_rsvp: RSVPResponse | None = None
        if user_id is not None:
            att = await self._repo.get_attendance(event.id, user_id)
            if att is not None:
                user_rsvp = RSVPResponse.model_validate(att)

        slots = self._slots_from_db(event.contribution_slots)

        return EventResponse(
            id=event.id,
            author_id=event.author_id,
            title=event.title,
            description=event.description,
            location=event.location,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            is_all_day=event.is_all_day,
            recurrence_rule=event.recurrence_rule,
            recurrence_id=event.recurrence_id,
            ical_uid=event.ical_uid,
            visibility=event.visibility,
            subgroup_id=event.subgroup_id,
            rsvp_labels=dict(event.rsvp_labels) if event.rsvp_labels else None,
            contribution_slots=slots,
            rsvp_counts=rsvp_counts,
            user_rsvp=user_rsvp,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )

    # ── CRUD ──────────────────────────────────────────────────────────

    async def create_event(self, user_id: uuid.UUID, data: EventCreate) -> EventResponse:
        if data.recurrence_rule:
            try:
                rrulestr(data.recurrence_rule, dtstart=data.starts_at)
            except Exception as exc:  # noqa: BLE001
                raise AppError(
                    code="INVALID_RRULE",
                    message=_("Recurrence rule is invalid"),
                    status_code=400,
                ) from exc

        if data.visibility == "subgroup" and data.subgroup_id is None:
            raise AppError(
                code="SUBGROUP_REQUIRED",
                message=_("Subgroup is required for subgroup-scoped events"),
                status_code=400,
            )

        event = Event(
            community_id=self._community_id,
            author_id=user_id,
            title=data.title,
            description=data.description,
            location=data.location,
            starts_at=data.starts_at,
            ends_at=data.ends_at,
            is_all_day=data.is_all_day,
            recurrence_rule=data.recurrence_rule,
            ical_uid=str(uuid.uuid4()) + "@nexara",
            visibility=data.visibility,
            subgroup_id=data.subgroup_id,
            rsvp_labels=data.rsvp_labels,
            contribution_slots=self._slots_to_dicts(data.contribution_slots),
        )
        event = await self._repo.create(event)
        return await self._build_response(event, user_id=user_id)

    async def get_event(self, event_id: uuid.UUID, user_id: uuid.UUID) -> EventResponse:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        if not await self._can_view(event, user_id):
            raise AuthorizationError(_("You cannot view this event"))
        return await self._build_response(event, user_id=user_id)

    async def update_event(
        self, event_id: uuid.UUID, user_id: uuid.UUID, data: EventUpdate
    ) -> EventResponse:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        if event.author_id != user_id:
            raise AuthorizationError(_("Only the event organizer can edit this event"))

        update_data = data.model_dump(exclude_unset=True)

        if "recurrence_rule" in update_data and update_data["recurrence_rule"]:
            try:
                rrulestr(update_data["recurrence_rule"], dtstart=event.starts_at)
            except Exception as exc:  # noqa: BLE001
                raise AppError(
                    code="INVALID_RRULE",
                    message=_("Recurrence rule is invalid"),
                    status_code=400,
                ) from exc

        if "contribution_slots" in update_data and update_data["contribution_slots"] is not None:
            slots = [ContributionSlot.model_validate(s) for s in update_data["contribution_slots"]]
            update_data["contribution_slots"] = self._slots_to_dicts(slots)

        update_data["updated_at"] = datetime.now(UTC)
        event = await self._repo.update(event, update_data)
        return await self._build_response(event, user_id=user_id)

    async def delete_event(self, event_id: uuid.UUID, user_id: uuid.UUID) -> None:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        if event.author_id != user_id:
            raise AuthorizationError(_("Only the event organizer can delete this event"))
        await self._session.delete(event)
        await self._session.flush()

    async def list_events(
        self,
        user_id: uuid.UUID,
        start: datetime,
        end: datetime,
        *,
        cursor: str | None = None,
        limit: int = 100,
    ) -> EventList:
        subgroup_ids = await self._user_subgroup_ids(user_id)
        events = await self._repo.list_in_range(
            self._community_id,
            start,
            end,
            viewer_id=user_id,
            subgroup_ids=subgroup_ids,
        )
        # Build responses including expanded occurrences for recurring events.
        responses: list[EventResponse] = []
        for event in events[: limit + 1]:
            responses.append(await self._build_response(event, user_id=user_id))
        next_cursor: str | None = None
        if len(responses) > limit:
            responses = responses[:limit]
            next_cursor = str(responses[-1].id)
        return EventList(items=responses, next_cursor=next_cursor, has_more=next_cursor is not None)

    # ── RRULE expansion ───────────────────────────────────────────────

    def expand_occurrences(
        self, event: Event, start: datetime, end: datetime
    ) -> list[EventOccurrence]:
        if event.recurrence_rule is None:
            return [
                EventOccurrence(
                    event_id=event.id,
                    starts_at=event.starts_at,
                    ends_at=event.ends_at,
                )
            ]

        try:
            rule = rrulestr(event.recurrence_rule, dtstart=event.starts_at)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "expand_occurrences_invalid_rrule",
                event_id=str(event.id),
                error=str(exc),
            )
            return []

        duration = event.ends_at - event.starts_at
        occurrences: list[EventOccurrence] = []
        for dt in rule.between(start, end, inc=True):
            occurrences.append(
                EventOccurrence(
                    event_id=event.id,
                    starts_at=dt,
                    ends_at=dt + duration,
                )
            )
            if len(occurrences) >= MAX_OCCURRENCES:
                break
        return occurrences

    # ── RSVP ──────────────────────────────────────────────────────────

    async def rsvp(
        self, event_id: uuid.UUID, user_id: uuid.UUID, data: RSVPRequest
    ) -> RSVPResponse:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        if not await self._can_view(event, user_id):
            raise AuthorizationError(_("You cannot RSVP to this event"))

        labels = dict(event.rsvp_labels) if event.rsvp_labels else dict(DEFAULT_RSVP_LABELS)
        if data.status not in labels:
            raise AppError(
                code="INVALID_RSVP_STATUS",
                message=_("RSVP status is not allowed for this event"),
                status_code=400,
            )

        att = await self._repo.upsert_attendance(
            event_id=event_id,
            user_id=user_id,
            community_id=self._community_id,
            status=data.status,
            note=data.note,
        )

        if self._notifications and event.author_id != user_id:
            try:
                await self._notifications.notify(
                    user_id=event.author_id,
                    type="event_rsvp",
                    payload={
                        "event_id": str(event.id),
                        "status": data.status,
                        "message": _("Someone RSVP'd to your event"),
                        "link": f"/app/events/{event.id}",
                    },
                    actor_id=user_id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("rsvp_notify_failed", error=str(exc))

        return RSVPResponse.model_validate(att)

    async def list_rsvps(self, event_id: uuid.UUID, user_id: uuid.UUID) -> list[RSVPResponse]:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        if not await self._can_view(event, user_id):
            raise AuthorizationError(_("You cannot view this event"))
        records = await self._repo.list_attendance(event_id)
        return [RSVPResponse.model_validate(r) for r in records]

    async def cancel_rsvp(self, event_id: uuid.UUID, user_id: uuid.UUID) -> None:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        await self._repo.remove_attendance(event_id, user_id)

    # ── Contributions ─────────────────────────────────────────────────

    async def claim_contribution(
        self,
        event_id: uuid.UUID,
        slot_id: uuid.UUID,
        user_id: uuid.UUID,
        data: ContributionClaim,
    ) -> EventResponse:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        if not await self._can_view(event, user_id):
            raise AuthorizationError(_("You cannot claim contributions on this event"))

        slots = self._slots_from_db(event.contribution_slots)
        target = next((s for s in slots if s.id == slot_id), None)
        if target is None:
            raise NotFoundError(_("Contribution slot not found"))

        remaining = target.quantity_needed - target.quantity_claimed
        if data.quantity > remaining:
            raise AppError(
                code="SLOT_FULL",
                message=_("Not enough remaining capacity on this slot"),
                status_code=400,
            )
        target.quantity_claimed += data.quantity
        if user_id not in target.claimed_by:
            target.claimed_by.append(user_id)

        event = await self._repo.update(
            event,
            {
                "contribution_slots": self._slots_to_dicts(slots),
                "updated_at": datetime.now(UTC),
            },
        )
        return await self._build_response(event, user_id=user_id)

    async def unclaim_contribution(
        self, event_id: uuid.UUID, slot_id: uuid.UUID, user_id: uuid.UUID
    ) -> EventResponse:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))

        slots = self._slots_from_db(event.contribution_slots)
        target = next((s for s in slots if s.id == slot_id), None)
        if target is None:
            raise NotFoundError(_("Contribution slot not found"))

        if user_id in target.claimed_by:
            target.claimed_by.remove(user_id)
            target.quantity_claimed = max(0, target.quantity_claimed - 1)

        event = await self._repo.update(
            event,
            {
                "contribution_slots": self._slots_to_dicts(slots),
                "updated_at": datetime.now(UTC),
            },
        )
        return await self._build_response(event, user_id=user_id)

    # ── iCal export ───────────────────────────────────────────────────

    def to_ical(self, events: list[Event]) -> bytes:
        cal = ICalCalendar()  # type: ignore[no-untyped-call]
        cal.add("prodid", "-//Nexara//EN")
        cal.add("version", "2.0")
        for event in events:
            ical_event = ICalEvent()  # type: ignore[no-untyped-call]
            ical_event.add("uid", event.ical_uid)
            ical_event.add("summary", event.title)
            if event.description:
                ical_event.add("description", event.description)
            if event.location:
                ical_event.add("location", event.location)
            ical_event.add("dtstart", event.starts_at)
            ical_event.add("dtend", event.ends_at)
            ical_event.add("dtstamp", event.created_at or datetime.now(UTC))
            if event.recurrence_rule:
                # icalendar accepts a raw RRULE string via vRecur
                from icalendar.prop import vRecur

                ical_event["rrule"] = vRecur.from_ical(event.recurrence_rule)
            cal.add_component(ical_event)
        return cal.to_ical()  # type: ignore[no-any-return]

    async def export_event_ical(self, event_id: uuid.UUID, user_id: uuid.UUID) -> bytes:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        if not await self._can_view(event, user_id):
            raise AuthorizationError(_("You cannot view this event"))
        return self.to_ical([event])

    async def export_feed_ical(self, user_id: uuid.UUID) -> bytes:
        now = datetime.now(UTC)
        end = now + timedelta(days=365)
        subgroup_ids = await self._user_subgroup_ids(user_id)
        events = await self._repo.list_in_range(
            self._community_id,
            now - timedelta(days=30),
            end,
            viewer_id=user_id,
            subgroup_ids=subgroup_ids,
        )
        return self.to_ical(events)

    # ── Subscriptions ─────────────────────────────────────────────────

    async def create_subscription(
        self, user_id: uuid.UUID, data: CalendarSubscriptionCreate
    ) -> CalendarSubscriptionResponse:
        sub = CalendarSubscription(
            community_id=self._community_id,
            user_id=user_id,
            name=data.name,
            color=data.color,
            source_type=data.source_type,
            source_url=data.source_url,
            visibility=data.visibility,
        )
        sub = await self._repo.create_subscription(sub)
        return CalendarSubscriptionResponse.model_validate(sub)

    async def list_subscriptions(self, user_id: uuid.UUID) -> list[CalendarSubscriptionResponse]:
        rows = await self._repo.list_subscriptions(self._community_id, user_id)
        return [CalendarSubscriptionResponse.model_validate(r) for r in rows]

    async def delete_subscription(self, sub_id: uuid.UUID, user_id: uuid.UUID) -> None:
        sub = await self._repo.get_subscription(sub_id, user_id=user_id)
        if sub is None:
            raise NotFoundError(_("Calendar subscription not found"))
        await self._repo.delete_subscription(sub_id)

    # ── Sync (called from Celery task) ────────────────────────────────

    async def sync_subscription(self, sub: CalendarSubscription, ical_bytes: bytes) -> int:
        """
        @brief Upsert events from an iCal feed bound to a subscription.

        @param sub The subscription owning the imported events.
        @param ical_bytes Raw iCal feed body.
        @return Number of events upserted (created or updated).
        """
        try:
            cal = ICalCalendar.from_ical(ical_bytes)
        except Exception as exc:  # noqa: BLE001
            sub.sync_error = f"parse_error: {exc}"
            await self._session.flush()
            return 0

        upserted = 0
        for component in cal.walk("VEVENT"):
            uid = str(component.get("uid"))  # type: ignore[no-untyped-call]
            if not uid:
                continue
            existing = await self._repo.get_by_ical_uid(uid)
            rrule = component.get("rrule")  # type: ignore[no-untyped-call]
            data: dict[str, Any] = {
                "title": str(component.get("summary") or ""),  # type: ignore[no-untyped-call]
                "description": str(component.get("description") or "") or None,  # type: ignore[no-untyped-call]
                "location": str(component.get("location") or "") or None,  # type: ignore[no-untyped-call]
                "starts_at": component.decoded("dtstart"),
                "ends_at": component.decoded("dtend") or component.decoded("dtstart"),
                "recurrence_rule": (rrule.to_ical().decode("utf-8") if rrule else None),
                "source_subscription_id": sub.id,
                "source_removed": False,
            }
            if existing is None:
                event = Event(
                    community_id=self._community_id,
                    author_id=sub.user_id,
                    ical_uid=uid,
                    visibility=sub.visibility,
                    **data,
                )
                await self._repo.create(event)
            else:
                await self._repo.update(existing, data)
            upserted += 1

        sub.last_synced_at = datetime.now(UTC)
        sub.sync_error = None
        await self._session.flush()
        return upserted
