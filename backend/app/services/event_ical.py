"""
@file event_ical.py
@brief iCal export, read-only token feeds and subscription sync for events.

Mixed into :class:`app.services.event_service.EventService`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import httpx
from icalendar import Calendar as ICalCalendar
from icalendar import Event as ICalEvent
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.http_safe import UnsafeUrlError, safe_fetch
from app.core.i18n import _
from app.models.event import CalendarSubscription, Event
from app.repositories.event_repo import EventRepository

FEED_MAX_SPAN_DAYS = 731  # ~2 years
_PARTSTAT = {"attending": "ACCEPTED", "maybe": "TENTATIVE"}


def _as_utc(dt: datetime) -> datetime:
    """@brief Treat naive datetimes as UTC so they compare with aware ones."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


class EventIcalMixin:
    """@brief iCal behaviour; relies on EventService state and visibility helpers."""

    _repo: EventRepository
    _community_id: uuid.UUID
    _session: AsyncSession
    _token_repo: Any

    if TYPE_CHECKING:

        async def _can_view(self, event: Event, user_id: uuid.UUID) -> bool: ...

        async def _user_subgroup_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]: ...

    # ── iCal export ───────────────────────────────────────────────────

    def to_ical(
        self,
        events: list[Event],
        people: dict[uuid.UUID, dict[str, Any]] | None = None,
    ) -> bytes:
        """@brief Serialize events; people maps event id -> organizer/attendees."""
        cal = ICalCalendar()  # type: ignore[no-untyped-call] # icalendar is untyped
        cal.add("prodid", "-//Nexara//EN")
        cal.add("version", "2.0")
        for event in events:
            ical_event = ICalEvent()  # type: ignore[no-untyped-call] # icalendar is untyped
            ical_event.add("uid", event.ical_uid)
            ical_event.add("summary", event.title)
            if event.description:
                ical_event.add("description", event.description)
            if event.location:
                ical_event.add("location", event.location)
            ical_event.add("dtstart", event.starts_at)
            ical_event.add("dtend", event.ends_at)
            ical_event.add("dtstamp", event.created_at or datetime.now(UTC))
            info = (people or {}).get(event.id)
            if info:
                if info.get("organizer"):
                    uid, name = info["organizer"]
                    ical_event.add("organizer", f"urn:uuid:{uid}", parameters={"CN": str(name)})
                for uid, name, status in info.get("attendees", []):
                    ical_event.add(
                        "attendee",
                        f"urn:uuid:{uid}",
                        parameters={
                            "CN": str(name),
                            "PARTSTAT": _PARTSTAT.get(status, "NEEDS-ACTION"),
                        },
                    )
            if event.recurrence_rule:
                # icalendar accepts a raw RRULE string via vRecur
                from icalendar.prop import vRecur

                ical_event["rrule"] = vRecur.from_ical(event.recurrence_rule)
            cal.add_component(ical_event)
        return cal.to_ical()  # type: ignore[no-any-return] # third-party stub returns Any

    async def export_event_ical(self, event_id: uuid.UUID, user_id: uuid.UUID) -> bytes:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        if not await self._can_view(event, user_id):
            raise AuthorizationError(_("You cannot view this event"))
        return self.to_ical([event], await self._repo.get_ical_people([event], viewer_id=user_id))

    async def export_feed_ical(
        self,
        user_id: uuid.UUID,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> bytes:
        """@brief Export visible events in [start, end] (default -30d..+365d)."""
        now = datetime.now(UTC)
        start = _as_utc(start) if start else now - timedelta(days=30)
        end = _as_utc(end) if end else now + timedelta(days=365)
        if start > end:
            raise AppError(
                code="invalid_range", message=_("start must not be after end"), status_code=422
            )
        if end - start > timedelta(days=FEED_MAX_SPAN_DAYS):
            raise AppError(
                code="range_too_large", message=_("Range must not exceed 2 years"), status_code=422
            )
        subgroup_ids = await self._user_subgroup_ids(user_id)
        events = await self._repo.list_in_range(
            self._community_id,
            start,
            end,
            viewer_id=user_id,
            subgroup_ids=subgroup_ids,
        )
        return self.to_ical(events, await self._repo.get_ical_people(events, viewer_id=user_id))

    # ── iCal token issuance & serving ──────────────────────────────────

    async def issue_ical_token(self, user_id: uuid.UUID) -> tuple[str, str]:
        """@brief Issue a read-only iCal token for external subscription.

        @param user_id User to issue token for.
        @return Tuple of (raw_token, feed_url).
        """
        raw, _token = await self._token_repo.issue(user_id=user_id, scope="ical")
        settings = get_settings()
        url = f"{settings.APP_BASE_URL}/api/v1/calendars/feed.ics?token={raw}"
        return raw, url

    async def serve_ical_for_token(self, raw_token: str) -> bytes:
        """@brief Retrieve and serve iCal feed for a read-only token.

        @param raw_token Raw token string (e.g. from query param).
        @return iCal bytes.
        @raises AuthorizationError if token invalid or revoked.
        """
        token = await self._token_repo.verify(raw_token)
        if token is None:
            raise AuthorizationError(_("Invalid or revoked iCal token"))

        user_id = token.user_id
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
        return self.to_ical(events, await self._repo.get_ical_people(events, viewer_id=user_id))

    # ── Subscription sync ─────────────────────────────────────────────

    async def sync_now(self, sub_id: uuid.UUID, user_id: uuid.UUID) -> int:
        """
        @brief Fetch and upsert one of the user's subscriptions immediately.

        @return Number of events upserted.
        """
        sub = await self._repo.get_subscription(sub_id, user_id=user_id)
        if sub is None or not sub.source_url:
            raise NotFoundError(_("Calendar subscription not found"))
        try:
            body = await safe_fetch(sub.source_url)
        except (UnsafeUrlError, httpx.HTTPError) as exc:
            sub.sync_error = f"fetch_error: {exc}"
            # Commit first: the raised error would roll back the request session
            # and lose sync_error otherwise.
            await self._session.commit()
            status = 422 if isinstance(exc, UnsafeUrlError) else 502
            raise AppError(
                message=_("Could not fetch calendar"), code="sync_failed", status_code=status
            ) from exc
        return await self.sync_subscription(sub, body)

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
            uid = str(component.get("uid"))  # type: ignore[no-untyped-call] # icalendar is untyped
            if not uid:
                continue
            # Namespace imported UIDs per subscription: a feed must never match
            # a native event or another user's import (ical_uid is unique).
            local_uid = f"{sub.id}:{uid}"
            existing = await self._repo.get_by_ical_uid(
                local_uid, uid, subscription_id=sub.id, community_id=self._community_id
            )
            # Skip upsert if event has been locally modified by user
            if existing is not None and existing.locally_modified:
                continue
            rrule = component.get("rrule")  # type: ignore[no-untyped-call] # icalendar is untyped
            data: dict[str, Any] = {
                # icalendar is untyped
                "title": str(component.get("summary") or ""),  # type: ignore[no-untyped-call]
                # icalendar is untyped
                "description": str(component.get("description") or "") or None,  # type: ignore[no-untyped-call]
                # icalendar is untyped
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
                    ical_uid=local_uid,
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
