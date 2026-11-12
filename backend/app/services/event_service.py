"""
@file event_service.py
@brief Event business logic — CRUD, RSVP, contributions, RRULE expansion, iCal.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import structlog
from dateutil.rrule import rrulestr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_search_cache_for_community
from app.core.config import get_settings
from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.event import CalendarSubscription, Event
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.activity_repo import ActivityRepository
from app.repositories.calendar_repo import CalendarRepository
from app.repositories.event_repo import EventRepository
from app.schemas.event import (
    CalendarSubscriptionCreate,
    CalendarSubscriptionResponse,
    CalendarSubscriptionUpdate,
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
from app.services.activity_publish import record_activity
from app.services.calendar_service import CalendarService
from app.services.event_gallery import create_event_gallery, find_event_gallery_id
from app.services.event_ical import EventIcalMixin

logger = structlog.get_logger(__name__)

DEFAULT_RSVP_LABELS: dict[str, str] = {
    "attending": "Attending",
    "maybe": "Maybe",
    "declined": "Declined",
}

# Maximum number of recurrence occurrences expanded per query window.
MAX_OCCURRENCES = 200


class EventService(EventIcalMixin):
    """@brief Service layer for events, RSVPs, and calendar subscriptions."""

    def __init__(
        self,
        event_repo: EventRepository,
        community_id: uuid.UUID,
        session: AsyncSession,
        *,
        actor_id: uuid.UUID | None = None,
        notification_service: Any | None = None,
        calendar_service: CalendarService | None = None,
        token_repo: Any | None = None,
        activity_repo: ActivityRepository | None = None,
    ) -> None:
        self._repo = event_repo
        self._community_id = community_id
        self._session = session
        self._actor_id = actor_id
        self._notifications = notification_service
        self._calendars = calendar_service or CalendarService(
            calendar_repo=CalendarRepository(session),
            community_id=community_id,
            session=session,
        )
        if token_repo is None:
            from app.repositories.calendar_token_repo import CalendarTokenRepository

            token_repo = CalendarTokenRepository(session)
        self._token_repo = token_repo
        self._activity_repo = activity_repo

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

    async def _subgroup_slug(self, subgroup_id: uuid.UUID | None) -> str | None:
        """@brief Return the URL slug for a subgroup, or None if not found."""
        if subgroup_id is None:
            return None
        result = await self._session.execute(
            select(Subgroup.slug).where(Subgroup.id == subgroup_id)
        )
        return result.scalar_one_or_none()

    async def _build_response(
        self,
        event: Event,
        *,
        user_id: uuid.UUID | None = None,
        gallery_id: uuid.UUID | None = None,
    ) -> EventResponse:
        rsvp_counts = await self._repo.rsvp_counts(event.id)
        user_rsvp: RSVPResponse | None = None
        if user_id is not None:
            att = await self._repo.get_attendance(event.id, user_id)
            if att is not None:
                user_rsvp = RSVPResponse.model_validate(att)

        slots = self._slots_from_db(event.contribution_slots)
        # TODO(home-redesign): batch subgroup_slug lookups across event list responses
        # (currently one query per event in _build_response).
        subgroup_slug = await self._subgroup_slug(event.subgroup_id)
        gallery_id = gallery_id or await find_event_gallery_id(
            self._session, self._community_id, event.id
        )

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
            subgroup_slug=subgroup_slug,
            calendar_id=event.calendar_id,
            color=event.color,
            latitude=event.latitude,
            longitude=event.longitude,
            rsvp_labels=dict(event.rsvp_labels) if event.rsvp_labels else None,
            contribution_slots=slots,
            reminder_offsets_minutes=event.reminder_offsets_minutes,
            rsvp_counts=rsvp_counts,
            user_rsvp=user_rsvp,
            gallery_id=gallery_id,
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

        calendar_id = await self._calendars.derive_calendar_id(
            user_id=user_id,
            visibility=data.visibility,
            subgroup_id=data.subgroup_id,
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
            calendar_id=calendar_id,
            color=data.color,
            latitude=data.latitude,
            longitude=data.longitude,
            rsvp_labels=data.rsvp_labels,
            contribution_slots=self._slots_to_dicts(data.contribution_slots),
            reminder_offsets_minutes=data.reminder_offsets_minutes,
        )
        event = await self._repo.create(event)

        if self._activity_repo is not None:
            from app.models.user import User

            user_result = await self._session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            user_name = user.display_name if user else "Unknown"

            await record_activity(
                self._activity_repo,
                self._session,
                None,
                community_id=self._community_id,
                actor_id=user_id,
                verb="event.created",
                object_type="event",
                object_id=event.id,
                subgroup_id=event.subgroup_id,
                visibility=event.visibility,
                target_type="subgroup" if event.subgroup_id else "community",
                target_id=event.subgroup_id or self._community_id,
                metadata={
                    "actor_name": user_name,
                    "object_title": event.title,
                },
            )

        await invalidate_search_cache_for_community(self._community_id)
        gallery_id = None
        if data.auto_create_gallery:
            gallery_id = await create_event_gallery(
                self._session, self._community_id, user_id, event
            )
        return await self._build_response(event, user_id=user_id, gallery_id=gallery_id)

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
        await invalidate_search_cache_for_community(self._community_id)
        return await self._build_response(event, user_id=user_id)

    async def delete_event(self, event_id: uuid.UUID, user_id: uuid.UUID) -> None:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        if event.author_id != user_id:
            raise AuthorizationError(_("Only the event organizer can delete this event"))
        await self._session.delete(event)
        await self._session.flush()
        await invalidate_search_cache_for_community(self._community_id)
        if self._activity_repo is not None:
            await self._activity_repo.invalidate("event", event_id)

    async def list_events(
        self,
        user_id: uuid.UUID,
        start: datetime,
        end: datetime,
        *,
        cursor: str | None = None,
        limit: int = 100,
        subgroup_id: uuid.UUID | None = None,
    ) -> EventList:
        subgroup_ids = await self._user_subgroup_ids(user_id)
        events = await self._repo.list_in_range(
            self._community_id,
            start,
            end,
            viewer_id=user_id,
            subgroup_ids=subgroup_ids,
            subgroup_id=subgroup_id,
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

    async def _actor_name(self, user_id: uuid.UUID) -> str:
        """@brief Display name of ``user_id`` for notification payloads."""
        user = await self._session.get(User, user_id)
        return str(user.display_name) if user is not None else _("Someone")

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
                        "actor_name": await self._actor_name(user_id),
                        "event_title": event.title,
                        "message": _("Someone RSVP'd to your event"),
                        "link": f"/app/events/{event.id}",
                    },
                    actor_id=user_id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("rsvp_notify_failed", error=str(exc))

        if self._activity_repo is not None:
            from app.models.user import User

            user_result = await self._session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            user_name = user.display_name if user else "Unknown"

            rsvp_id = att.id if hasattr(att, "id") else uuid.uuid4()
            await record_activity(
                self._activity_repo,
                self._session,
                None,
                community_id=self._community_id,
                actor_id=user_id,
                verb="event.rsvp",
                object_type="rsvp",
                object_id=rsvp_id,
                subgroup_id=event.subgroup_id,
                visibility=event.visibility,
                target_type="event",
                target_id=event_id,
                metadata={
                    "actor_name": user_name,
                    "object_title": event.title,
                },
            )

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

    # ── RRULE exception occurrences ───────────────────────────────────

    def _append_until(self, rrule_str: str, until: str) -> str:
        """@brief Strip existing UNTIL and append a new one to RRULE.

        @param rrule_str RRULE string (e.g. 'FREQ=WEEKLY;COUNT=4').
        @param until ISO 8601 datetime string (e.g. '20260508T175959Z').
        @return Modified RRULE with UNTIL appended.
        """
        # Remove any existing UNTIL= clause
        modified = re.sub(r";UNTIL=[^;]*", "", rrule_str)
        # Remove any existing COUNT= clause (UNTIL and COUNT are mutually exclusive)
        modified = re.sub(r";COUNT=\d+", "", modified)
        # Append UNTIL
        if modified.endswith(";"):
            return f"{modified}UNTIL={until}"
        return f"{modified};UNTIL={until}"

    async def update_occurrence(
        self,
        parent_id: uuid.UUID,
        occurrence_start: datetime,
        scope: Literal["this", "this_and_following", "all"],
        payload: dict[str, Any],
    ) -> Event:
        """@brief Update a single occurrence of a recurring event.

        @param parent_id UUID of the recurring parent event.
        @param occurrence_start Datetime of the occurrence to modify.
        @param scope Update scope:
            - 'this': create child override for this occurrence only.
            - 'this_and_following': truncate parent rule, create new series from this date.
            - 'all': update the parent event directly.
        @param payload Fields to update (title, description, etc.).
        @return The modified or new Event.
        @raises NotFoundError if parent not found or not recurring.
        @raises AuthorizationError if user is not the organizer.
        """
        parent = await self._repo.get_by_id(parent_id, community_id=self._community_id)
        if parent is None or not parent.recurrence_rule:
            raise NotFoundError(_("Recurring event not found"))

        # Authorize: only organizer can edit
        if parent.author_id != self._actor_id:
            raise AuthorizationError(_("Only the event organizer can edit this event"))

        if scope == "all":
            # Update the parent event directly
            update_data = {**payload, "updated_at": datetime.now(UTC)}
            return await self._repo.update(parent, update_data)

        if scope == "this":
            # Create a child override event
            child_data = {
                "community_id": parent.community_id,
                "author_id": self._actor_id,
                "title": payload.get("title", parent.title),
                "description": payload.get("description", parent.description),
                "location": payload.get("location", parent.location),
                "starts_at": occurrence_start,
                "ends_at": occurrence_start + (parent.ends_at - parent.starts_at),
                "is_all_day": payload.get("is_all_day", parent.is_all_day),
                "recurrence_rule": None,
                "recurrence_id": parent.id,
                "original_start": occurrence_start,
                "ical_uid": str(uuid.uuid4()) + "@nexara",
                "visibility": payload.get("visibility", parent.visibility),
                "subgroup_id": payload.get("subgroup_id", parent.subgroup_id),
                "calendar_id": parent.calendar_id,
                "color": payload.get("color", parent.color),
                "latitude": payload.get("latitude", parent.latitude),
                "longitude": payload.get("longitude", parent.longitude),
                "rsvp_labels": payload.get("rsvp_labels", parent.rsvp_labels),
                "contribution_slots": payload.get("contribution_slots", parent.contribution_slots),
                "reminder_offsets_minutes": payload.get(
                    "reminder_offsets_minutes", parent.reminder_offsets_minutes
                ),
            }
            child = Event(**child_data)
            return await self._repo.create(child)

        # scope == "this_and_following"
        # Truncate parent RRULE with UNTIL = (occurrence_start - 1 second)
        until_dt = occurrence_start - timedelta(seconds=1)
        until_str = until_dt.strftime("%Y%m%dT%H%M%SZ")
        new_rule = self._append_until(parent.recurrence_rule, until_str)
        await self._repo.update(parent, {"recurrence_rule": new_rule})

        # Create new recurring event starting from this occurrence
        new_data = {
            "community_id": parent.community_id,
            "author_id": self._actor_id,
            "title": payload.get("title", parent.title),
            "description": payload.get("description", parent.description),
            "location": payload.get("location", parent.location),
            "starts_at": occurrence_start,
            "ends_at": occurrence_start + (parent.ends_at - parent.starts_at),
            "is_all_day": payload.get("is_all_day", parent.is_all_day),
            "recurrence_rule": parent.recurrence_rule,
            "recurrence_id": None,
            "original_start": None,
            "ical_uid": str(uuid.uuid4()) + "@nexara",
            "visibility": payload.get("visibility", parent.visibility),
            "subgroup_id": payload.get("subgroup_id", parent.subgroup_id),
            "calendar_id": parent.calendar_id,
            "color": payload.get("color", parent.color),
            "latitude": payload.get("latitude", parent.latitude),
            "longitude": payload.get("longitude", parent.longitude),
            "rsvp_labels": payload.get("rsvp_labels", parent.rsvp_labels),
            "contribution_slots": payload.get("contribution_slots", parent.contribution_slots),
            "reminder_offsets_minutes": payload.get(
                "reminder_offsets_minutes", parent.reminder_offsets_minutes
            ),
        }
        new_event = Event(**new_data)
        return await self._repo.create(new_event)

    # ── Subscriptions ─────────────────────────────────────────────────

    async def create_subscription(
        self, user_id: uuid.UUID, data: CalendarSubscriptionCreate, *, is_admin: bool = False
    ) -> CalendarSubscriptionResponse:
        # Reject shared_by_admin=True if not admin
        if data.shared_by_admin and not is_admin:
            raise AuthorizationError(_("Only admins can create shared subscriptions"))

        # Enforce per-user subscription cap
        count = await self._repo.count_subscriptions_for(user_id)
        settings = get_settings()
        if count >= settings.CALENDAR_SUBS_PER_USER_MAX:
            raise AppError(
                message="Subscription limit reached",
                code="subscription_limit",
            )

        sub = CalendarSubscription(
            community_id=self._community_id,
            user_id=user_id,
            name=data.name,
            color=data.color,
            source_type=data.source_type,
            source_url=data.source_url,
            visibility=data.visibility,
            shared_by_admin=data.shared_by_admin,
            sync_interval_minutes=data.sync_interval_minutes,
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

    async def update_subscription(
        self, sub_id: uuid.UUID, user_id: uuid.UUID, data: CalendarSubscriptionUpdate
    ) -> CalendarSubscriptionResponse:
        """@brief Update name/url/enabled/interval of an owned subscription."""
        sub = await self._repo.get_subscription(sub_id, user_id=user_id)
        if sub is None:
            raise NotFoundError(_("Calendar subscription not found"))
        for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
            setattr(sub, field, value)
        sub = await self._repo.update_subscription(sub)
        return CalendarSubscriptionResponse.model_validate(sub)
