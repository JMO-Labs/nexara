"""
@file event_service.py
@brief Event business logic — CRUD and shared helpers; RSVP, recurrence,
       subscriptions and iCal live in sibling mixin modules.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from dateutil.rrule import rrulestr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_search_cache_for_community
from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.event import Event
from app.models.subgroup import SubgroupMember
from app.repositories.activity_repo import ActivityRepository
from app.repositories.calendar_repo import CalendarRepository
from app.repositories.event_repo import EventRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.schemas.event import (
    ContributionSlot,
    EventCreate,
    EventList,
    EventResponse,
    EventUpdate,
    RSVPResponse,
)
from app.services.activity_publish import record_activity
from app.services.calendar_service import CalendarService
from app.services.event_gallery import create_event_gallery, find_event_gallery_id
from app.services.event_ical import EventIcalMixin
from app.services.event_recurrence import MAX_OCCURRENCES, EventRecurrenceMixin
from app.services.event_rsvp import DEFAULT_RSVP_LABELS, EventRsvpMixin
from app.services.event_subscriptions import EventSubscriptionsMixin

__all__ = ["DEFAULT_RSVP_LABELS", "MAX_OCCURRENCES", "EventService"]


class EventService(
    EventIcalMixin,
    EventRsvpMixin,
    EventRecurrenceMixin,
    EventSubscriptionsMixin,
):
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
        subgroup_repo: SubgroupRepository | None = None,
    ) -> None:
        self._repo = event_repo
        self._subgroups = subgroup_repo or SubgroupRepository(session)
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

    async def _slug_map(self, events: list[Event]) -> dict[uuid.UUID, str]:
        """@brief Resolve subgroup slugs for ``events`` in a single query."""
        ids = list({e.subgroup_id for e in events if e.subgroup_id is not None})
        return await self._subgroups.get_slugs(ids, self._community_id)

    async def _build_response(
        self,
        event: Event,
        *,
        user_id: uuid.UUID | None = None,
        gallery_id: uuid.UUID | None = None,
        slugs: dict[uuid.UUID, str] | None = None,
    ) -> EventResponse:
        """@brief Build a response; pass ``slugs`` to skip the per-event lookup."""
        if slugs is None:
            slugs = await self._slug_map([event])
        rsvp_counts = await self._repo.rsvp_counts(event.id)
        user_rsvp: RSVPResponse | None = None
        if user_id is not None:
            att = await self._repo.get_attendance(event.id, user_id)
            if att is not None:
                user_rsvp = RSVPResponse.model_validate(att)

        slots = self._slots_from_db(event.contribution_slots)
        subgroup_slug = slugs.get(event.subgroup_id) if event.subgroup_id else None
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

        await invalidate_search_cache_for_community(
            self._community_id, service="event", action="create", user_id=user_id
        )
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
        await invalidate_search_cache_for_community(
            self._community_id, service="event", action="update", user_id=user_id
        )
        return await self._build_response(event, user_id=user_id)

    async def delete_event(self, event_id: uuid.UUID, user_id: uuid.UUID) -> None:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        if event.author_id != user_id:
            raise AuthorizationError(_("Only the event organizer can delete this event"))
        await self._session.delete(event)
        await self._session.flush()
        await invalidate_search_cache_for_community(
            self._community_id, service="event", action="delete", user_id=user_id
        )
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
        page = events[: limit + 1]
        slugs = await self._slug_map(page)
        for event in page:
            responses.append(await self._build_response(event, user_id=user_id, slugs=slugs))
        next_cursor: str | None = None
        if len(responses) > limit:
            responses = responses[:limit]
            next_cursor = str(responses[-1].id)
        return EventList(items=responses, next_cursor=next_cursor, has_more=next_cursor is not None)
