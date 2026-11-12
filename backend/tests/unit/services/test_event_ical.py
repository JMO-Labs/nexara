"""
@file test_event_ical.py
@brief Unit tests for iCal export, subscription sync-now and upsert.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import httpx

from app.core.exceptions import AppError, NotFoundError
from app.models.event import CalendarSubscription, Event
from app.repositories.event_repo import EventRepository
from app.schemas.event import CalendarSubscriptionResponse
from app.services.event_service import EventService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//x//EN
BEGIN:VEVENT
UID:ext-1@example.com
DTSTAMP:20260501T000000Z
DTSTART:20260601T100000Z
DTEND:20260601T110000Z
SUMMARY:Imported
END:VEVENT
END:VCALENDAR
"""


def _sub(**kw: object) -> MagicMock:
    sub = MagicMock(spec=CalendarSubscription)
    sub.id = uuid.uuid4()
    sub.user_id = kw.get("user_id", uuid.uuid4())
    sub.source_type = "ical"
    sub.source_url = "https://example.com/c.ics"
    sub.visibility = "private"
    sub.last_synced_at = kw.get("last_synced_at")
    sub.sync_interval_minutes = 60
    sub.sync_error = None
    return sub


@pytest.fixture
def repo() -> AsyncMock:
    r = AsyncMock(spec=EventRepository)
    r.get_by_ical_uid.return_value = None
    return r


@pytest.fixture
def service(repo: AsyncMock) -> EventService:
    return EventService(event_repo=repo, community_id=COMMUNITY_ID, session=AsyncMock())


def _event() -> MagicMock:
    e = MagicMock(spec=Event)
    e.title = "Picnic"
    e.description = "Bring food"
    e.location = "Park"
    e.starts_at = datetime(2026, 5, 1, 18, tzinfo=UTC)
    e.ends_at = datetime(2026, 5, 1, 20, tzinfo=UTC)
    e.recurrence_rule = "FREQ=WEEKLY;COUNT=3"
    e.ical_uid = "uid@nexara"
    e.created_at = datetime(2026, 4, 1, tzinfo=UTC)
    e.id = uuid.uuid4()
    return e


def test_to_ical_has_vevent_fields(service: EventService) -> None:
    ev = _event()
    people = {
        ev.id: {
            "organizer": ("Olga", "olga@example.com"),
            "attendees": [
                ("Ann", "ann@example.com", "attending"),
                ("Bob", "bob@example.com", "maybe"),
            ],
        }
    }
    body = service.to_ical([ev], people).decode()
    for token in (
        "BEGIN:VEVENT",
        "DTSTART",
        "DTEND",
        "RRULE:FREQ=WEEKLY",
        "SUMMARY:Picnic",
        "DESCRIPTION:Bring food",
        "LOCATION:Park",
        "UID:uid@nexara",
        "ORGANIZER;CN=Olga:mailto:olga@example.com",
        "ATTENDEE;CN=Ann;PARTSTAT=ACCEPTED:mailto:ann@example.com",
        "ATTENDEE;CN=Bob;PARTSTAT=TENTATIVE:mailto:bob@example.com",
    ):
        assert token in body


async def test_feed_uses_given_range(service: EventService, repo: AsyncMock) -> None:
    repo.list_in_range.return_value = []
    service._user_subgroup_ids = AsyncMock(return_value=[])  # type: ignore[method-assign]
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = start + timedelta(days=30)
    await service.export_feed_ical(uuid.uuid4(), start=start, end=end)
    assert repo.list_in_range.await_args.args[1:3] == (start, end)


async def test_sync_creates_new_uid(service: EventService, repo: AsyncMock) -> None:
    assert await service.sync_subscription(_sub(), ICS) == 1
    repo.create.assert_awaited_once()
    repo.update.assert_not_awaited()


async def test_sync_updates_existing_uid(service: EventService, repo: AsyncMock) -> None:
    existing = MagicMock(spec=Event)
    existing.locally_modified = False
    repo.get_by_ical_uid.return_value = existing
    assert await service.sync_subscription(_sub(), ICS) == 1
    repo.update.assert_awaited_once()
    repo.create.assert_not_awaited()


async def test_sync_now_fetches_and_upserts(service: EventService, repo: AsyncMock) -> None:
    uid = uuid.uuid4()
    sub = _sub(user_id=uid)
    repo.get_subscription.return_value = sub
    with patch("app.services.event_service.safe_fetch", AsyncMock(return_value=ICS)) as f:
        count = await service.sync_now(sub.id, uid)
    f.assert_awaited_once_with(sub.source_url)
    assert count == 1


async def test_sync_now_unknown_sub_404(service: EventService, repo: AsyncMock) -> None:
    repo.get_subscription.return_value = None
    with pytest.raises(NotFoundError):
        await service.sync_now(uuid.uuid4(), uuid.uuid4())


def test_response_next_sync_at() -> None:
    last = datetime(2026, 5, 1, 10, tzinfo=UTC)
    sub = _sub(last_synced_at=last)
    sub.name, sub.color, sub.source_type = "n", "#4285f4", "ical"
    sub.sync_enabled, sub.shared_by_admin = True, False
    sub.created_at = last
    r = CalendarSubscriptionResponse.model_validate(sub)
    assert r.next_sync_at == last + timedelta(minutes=60)


async def test_feed_rejects_start_after_end(service: EventService) -> None:
    start = datetime(2026, 6, 2, tzinfo=UTC)
    with pytest.raises(AppError) as ei:
        await service.export_feed_ical(uuid.uuid4(), start=start, end=start - timedelta(days=1))
    assert ei.value.status_code == 422


async def test_feed_rejects_span_over_two_years(service: EventService) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(AppError) as ei:
        await service.export_feed_ical(uuid.uuid4(), start=start, end=start + timedelta(days=732))
    assert ei.value.status_code == 422


async def test_sync_now_fetch_failure_sets_error_and_commits(
    service: EventService, repo: AsyncMock
) -> None:
    sub = _sub()
    repo.get_subscription.return_value = sub
    with patch(
        "app.services.event_service.safe_fetch", side_effect=httpx.ConnectError("boom")
    ):
        with pytest.raises(AppError) as ei:
            await service.sync_now(sub.id, sub.user_id)
    assert ei.value.code == "sync_failed"
    assert sub.sync_error.startswith("fetch_error")
    service._session.commit.assert_awaited()
