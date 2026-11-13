"""
@file test_event_ical_coverage.py
@brief Coverage for iCal edge paths: 404/403 export, parse errors, empty UID,
       empty people lookup, attendee rows, feed/sync routes, next_sync_at off.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.event import CalendarSubscription, Event
from app.repositories.event_repo import EventRepository
from app.schemas.event import CalendarSubscriptionResponse
from app.services.event_service import EventService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
EMPTY_UID_ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//x//EN
BEGIN:VEVENT
UID:
DTSTAMP:20260501T000000Z
DTSTART:20260601T100000Z
SUMMARY:No uid
END:VEVENT
END:VCALENDAR
"""


@pytest.fixture
def repo() -> AsyncMock:
    r = AsyncMock(spec=EventRepository)
    r.get_by_ical_uid.return_value = None
    return r


@pytest.fixture
def service(repo: AsyncMock) -> EventService:
    return EventService(event_repo=repo, community_id=COMMUNITY_ID, session=AsyncMock())


async def test_export_event_not_found(service: EventService, repo: AsyncMock) -> None:
    repo.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        await service.export_event_ical(uuid.uuid4(), USER_ID)


async def test_export_event_forbidden(service: EventService, repo: AsyncMock) -> None:
    repo.get_by_id.return_value = MagicMock(spec=Event)
    service._can_view = AsyncMock(return_value=False)  # type: ignore[method-assign]
    with pytest.raises(AuthorizationError):
        await service.export_event_ical(uuid.uuid4(), USER_ID)


async def test_sync_parse_error_sets_sync_error(service: EventService) -> None:
    sub = MagicMock(spec=CalendarSubscription)
    sub.id = uuid.uuid4()
    assert await service.sync_subscription(sub, b"\x00not an ical") == 0
    assert sub.sync_error.startswith("parse_error")


async def test_sync_skips_empty_uid(service: EventService, repo: AsyncMock) -> None:
    sub = MagicMock(spec=CalendarSubscription)
    sub.id = uuid.uuid4()
    assert await service.sync_subscription(sub, EMPTY_UID_ICS) == 0
    repo.get_by_ical_uid.assert_not_awaited()


async def test_ical_people_empty_events_short_circuits() -> None:
    session = AsyncMock()
    assert await EventRepository(session).get_ical_people([], viewer_id=USER_ID) == {}
    session.execute.assert_not_awaited()


async def test_ical_people_collects_attendees() -> None:
    ev = MagicMock(spec=Event)
    ev.id, ev.author_id = uuid.uuid4(), uuid.uuid4()
    ann = uuid.uuid4()
    authors = MagicMock()
    authors.all.return_value = [(ev.author_id, "Olga")]
    atts = MagicMock()
    atts.all.return_value = [(ev.id, ann, "Ann", "attending")]
    session = AsyncMock()
    session.execute.side_effect = [authors, atts]
    out = await EventRepository(session).get_ical_people([ev], viewer_id=USER_ID)
    assert out[ev.id]["organizer"] == (ev.author_id, "Olga")
    assert out[ev.id]["attendees"] == [(ann, "Ann", "attending")]


def test_next_sync_at_none_when_disabled() -> None:
    now = datetime(2026, 5, 1, tzinfo=UTC)
    r = CalendarSubscriptionResponse(
        id=uuid.uuid4(),
        name="n",
        color="#4285f4",
        source_type="ical_url",
        source_url="https://example.com/a.ics",
        visibility="private",
        sync_enabled=False,
        sync_interval_minutes=60,
        last_synced_at=None,
        sync_error=None,
        created_at=now,
    )
    assert r.next_sync_at is None


async def _client(test_app, service: AsyncMock) -> AsyncClient:
    from app.api.v1.events import _build_service
    from app.core.dependencies import get_current_user

    user = MagicMock()
    user.id = USER_ID
    user.is_active = True
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[_build_service] = lambda: service
    return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")


async def test_feed_ics_route(test_app) -> None:
    service = AsyncMock()
    service.export_feed_ical.return_value = b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"
    try:
        async with await _client(test_app, service) as c:
            r = await c.get("/api/v1/events/feed.ics")
    finally:
        test_app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    assert service.export_feed_ical.await_args.args[0] == USER_ID


async def test_sync_now_route(test_app) -> None:
    service = AsyncMock()
    service.sync_now.return_value = 3
    sub_id = uuid.uuid4()
    try:
        async with await _client(test_app, service) as c:
            r = await c.post(f"/api/v1/calendar-subscriptions/{sub_id}/sync")
    finally:
        test_app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json() == {"synced_count": 3}
    assert service.sync_now.await_args.args == (sub_id, USER_ID)
