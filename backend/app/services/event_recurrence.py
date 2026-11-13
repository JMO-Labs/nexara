"""
@file event_recurrence.py
@brief RRULE expansion and recurring-occurrence edits for events.

Mixed into :class:`app.services.event_service.EventService`.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import structlog
from dateutil.rrule import rrulestr

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.event import Event
from app.repositories.event_repo import EventRepository
from app.schemas.event import EventOccurrence

logger = structlog.get_logger(__name__)

# Maximum number of recurrence occurrences expanded per query window.
MAX_OCCURRENCES = 200


class EventRecurrenceMixin:
    """@brief Recurrence behaviour; relies on EventService state."""

    _repo: EventRepository
    _community_id: uuid.UUID
    _actor_id: uuid.UUID | None

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
