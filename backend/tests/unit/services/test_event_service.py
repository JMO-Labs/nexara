"""
@file test_event_service.py
@brief Unit tests for EventService.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.models.calendar_token import CalendarToken
from app.models.event import CalendarSubscription, Event, EventAttendance
from app.repositories.calendar_token_repo import CalendarTokenRepository
from app.repositories.event_repo import EventRepository
from app.schemas.event import (
    CalendarSubscriptionCreate,
    ContributionClaim,
    EventCreate,
    EventUpdate,
    RSVPRequest,
)
from app.services.calendar_service import CalendarService
from app.services.event_service import EventService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _make_event(
    *,
    author_id: uuid.UUID | None = None,
    visibility: str = "community",
    subgroup_id: uuid.UUID | None = None,
    recurrence_rule: str | None = None,
    rsvp_labels: dict[str, str] | None = None,
    contribution_slots: list[dict] | None = None,
    reminder_offsets_minutes: list[int] | None = None,
) -> MagicMock:
    event = MagicMock(spec=Event)
    event.id = uuid.uuid4()
    event.community_id = COMMUNITY_ID
    event.author_id = author_id or uuid.uuid4()
    event.title = "Test event"
    event.description = "desc"
    event.location = "loc"
    event.starts_at = datetime(2026, 5, 1, 18, 0, tzinfo=UTC)
    event.ends_at = datetime(2026, 5, 1, 20, 0, tzinfo=UTC)
    event.is_all_day = False
    event.recurrence_rule = recurrence_rule
    event.recurrence_id = None
    event.ical_uid = "uid@nexara"
    event.visibility = visibility
    event.subgroup_id = subgroup_id
    event.calendar_id = None
    event.color = None
    event.latitude = None
    event.longitude = None
    event.rsvp_labels = rsvp_labels
    event.contribution_slots = contribution_slots or []
    event.reminder_offsets_minutes = reminder_offsets_minutes or [60]
    event.created_at = datetime.now(UTC)
    event.updated_at = datetime.now(UTC)
    return event


@pytest.fixture
def repo() -> AsyncMock:
    r = AsyncMock(spec=EventRepository)
    r.rsvp_counts.return_value = {}
    r.get_attendance.return_value = None
    return r


@pytest.fixture
def session() -> AsyncMock:
    s = AsyncMock()
    exec_result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = []
    exec_result.scalars.return_value = scalars
    s.execute.return_value = exec_result
    return s


@pytest.fixture
def calendar_service() -> AsyncMock:
    cs = AsyncMock(spec=CalendarService)
    cs.derive_calendar_id.return_value = uuid.uuid4()
    return cs


@pytest.fixture
def service(
    repo: AsyncMock, session: AsyncMock, calendar_service: AsyncMock
) -> EventService:
    return EventService(
        event_repo=repo,
        community_id=COMMUNITY_ID,
        session=session,
        calendar_service=calendar_service,
    )


class TestCreateEvent:
    @pytest.mark.asyncio
    async def test_creates_event_with_valid_data(
        self, service: EventService, repo: AsyncMock
    ) -> None:
        user_id = uuid.uuid4()

        def _fill(e: Event) -> Event:
            e.id = uuid.uuid4()
            e.created_at = datetime.now(UTC)
            e.updated_at = datetime.now(UTC)
            return e

        repo.create.side_effect = _fill
        data = EventCreate(
            title="Picnic",
            starts_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
            ends_at=datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
        )
        result = await service.create_event(user_id, data)
        assert result.title == "Picnic"
        assert result.author_id == user_id

    @pytest.mark.asyncio
    async def test_invalid_rrule_rejected(self, service: EventService) -> None:
        user_id = uuid.uuid4()
        data = EventCreate(
            title="Bad",
            starts_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
            ends_at=datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
            recurrence_rule="not-a-real-rule",
        )
        with pytest.raises(AppError, match="invalid|RRULE"):
            await service.create_event(user_id, data)

    @pytest.mark.asyncio
    async def test_subgroup_visibility_requires_subgroup(self, service: EventService) -> None:
        user_id = uuid.uuid4()
        data = EventCreate(
            title="Subgroup-only",
            starts_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
            ends_at=datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
            visibility="subgroup",
        )
        with pytest.raises(AppError, match="[Ss]ubgroup"):
            await service.create_event(user_id, data)


class TestRRULEExpansion:
    def test_non_recurring_returns_single(self, service: EventService) -> None:
        event = _make_event()
        out = service.expand_occurrences(
            event,
            datetime(2026, 4, 1, tzinfo=UTC),
            datetime(2026, 6, 1, tzinfo=UTC),
        )
        assert len(out) == 1
        assert out[0].starts_at == event.starts_at

    def test_weekly_rrule_expands(self, service: EventService) -> None:
        event = _make_event(recurrence_rule="FREQ=WEEKLY;COUNT=4")
        out = service.expand_occurrences(
            event,
            datetime(2026, 4, 1, tzinfo=UTC),
            datetime(2026, 7, 1, tzinfo=UTC),
        )
        assert len(out) == 4
        # Each spaced 7 days apart
        deltas = [(out[i + 1].starts_at - out[i].starts_at).days for i in range(len(out) - 1)]
        assert all(d == 7 for d in deltas)


class TestRSVP:
    @pytest.mark.asyncio
    async def test_rsvp_creates_attendance(self, service: EventService, repo: AsyncMock) -> None:
        event = _make_event()
        repo.get_by_id.return_value = event
        att = MagicMock(spec=EventAttendance)
        att.id = uuid.uuid4()
        att.event_id = event.id
        att.user_id = uuid.uuid4()
        att.status = "attending"
        att.note = None
        att.responded_at = datetime.now(UTC)
        repo.upsert_attendance.return_value = att

        result = await service.rsvp(event.id, att.user_id, RSVPRequest(status="attending"))
        assert result.status == "attending"
        repo.upsert_attendance.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_custom_label_accepted(self, service: EventService, repo: AsyncMock) -> None:
        event = _make_event(rsvp_labels={"yes_food": "Yes + bringing food"})
        repo.get_by_id.return_value = event
        att = MagicMock(spec=EventAttendance)
        att.id = uuid.uuid4()
        att.event_id = event.id
        att.user_id = uuid.uuid4()
        att.status = "yes_food"
        att.note = None
        att.responded_at = datetime.now(UTC)
        repo.upsert_attendance.return_value = att

        result = await service.rsvp(event.id, att.user_id, RSVPRequest(status="yes_food"))
        assert result.status == "yes_food"

    @pytest.mark.asyncio
    async def test_invalid_label_rejected(self, service: EventService, repo: AsyncMock) -> None:
        event = _make_event()  # default labels only
        repo.get_by_id.return_value = event
        with pytest.raises(AppError, match="not allowed|status"):
            await service.rsvp(event.id, uuid.uuid4(), RSVPRequest(status="bogus"))

    @pytest.mark.asyncio
    async def test_rsvp_event_not_found(self, service: EventService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.rsvp(uuid.uuid4(), uuid.uuid4(), RSVPRequest(status="attending"))


class TestContributions:
    @pytest.mark.asyncio
    async def test_claim_slot(self, service: EventService, repo: AsyncMock) -> None:
        slot_id = uuid.uuid4()
        event = _make_event(
            contribution_slots=[
                {
                    "id": str(slot_id),
                    "title": "Drinks",
                    "quantity_needed": 3,
                    "quantity_claimed": 0,
                    "claimed_by": [],
                }
            ]
        )
        repo.get_by_id.return_value = event
        repo.update.side_effect = lambda e, d: MagicMock(
            spec=Event,
            **{
                **e.__dict__,
                **d,
                "id": e.id,
                "rsvp_labels": e.rsvp_labels,
                "contribution_slots": d.get("contribution_slots", e.contribution_slots),
                "starts_at": e.starts_at,
                "ends_at": e.ends_at,
                "created_at": e.created_at,
                "updated_at": d.get("updated_at", e.updated_at),
                "title": e.title,
                "description": e.description,
                "location": e.location,
                "is_all_day": e.is_all_day,
                "recurrence_rule": e.recurrence_rule,
                "recurrence_id": e.recurrence_id,
                "ical_uid": e.ical_uid,
                "visibility": e.visibility,
                "subgroup_id": e.subgroup_id,
                "author_id": e.author_id,
                "color": e.color,
            },
        )
        user_id = uuid.uuid4()
        result = await service.claim_contribution(
            event.id, slot_id, user_id, ContributionClaim(quantity=2)
        )
        assert result.contribution_slots[0].quantity_claimed == 2
        assert user_id in result.contribution_slots[0].claimed_by

    @pytest.mark.asyncio
    async def test_claim_too_much_rejected(self, service: EventService, repo: AsyncMock) -> None:
        slot_id = uuid.uuid4()
        event = _make_event(
            contribution_slots=[
                {
                    "id": str(slot_id),
                    "title": "Drinks",
                    "quantity_needed": 1,
                    "quantity_claimed": 1,
                    "claimed_by": [],
                }
            ]
        )
        repo.get_by_id.return_value = event
        with pytest.raises(AppError, match="capacity|full"):
            await service.claim_contribution(
                event.id, slot_id, uuid.uuid4(), ContributionClaim(quantity=1)
            )


class TestICalExport:
    @pytest.mark.asyncio
    async def test_event_ical_includes_basic_fields(
        self, service: EventService, repo: AsyncMock
    ) -> None:
        event = _make_event()
        repo.get_by_id.return_value = event
        body = await service.export_event_ical(event.id, event.author_id)
        text = body.decode("utf-8")
        assert "BEGIN:VCALENDAR" in text
        assert "BEGIN:VEVENT" in text
        assert "Test event" in text


class TestPermissions:
    @pytest.mark.asyncio
    async def test_private_event_hidden_from_others(
        self, service: EventService, repo: AsyncMock
    ) -> None:
        event = _make_event(visibility="private")
        repo.get_by_id.return_value = event
        with pytest.raises(AuthorizationError):
            await service.get_event(event.id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_only_organizer_can_delete(self, service: EventService, repo: AsyncMock) -> None:
        event = _make_event()
        repo.get_by_id.return_value = event
        with pytest.raises(AuthorizationError):
            await service.delete_event(event.id, uuid.uuid4())


class TestSubscriptions:
    @pytest.mark.asyncio
    async def test_create_subscription(self, service: EventService, repo: AsyncMock) -> None:
        sub = MagicMock(spec=CalendarSubscription)
        sub.id = uuid.uuid4()
        sub.community_id = COMMUNITY_ID
        sub.user_id = uuid.uuid4()
        sub.name = "Holidays"
        sub.color = "#4285f4"
        sub.source_type = "ical"
        sub.source_url = "https://example.com/feed.ics"
        sub.visibility = "private"
        sub.sync_enabled = True
        sub.last_synced_at = None
        sub.sync_error = None
        sub.created_at = datetime.now(UTC)
        repo.create_subscription.return_value = sub

        result = await service.create_subscription(
            sub.user_id,
            CalendarSubscriptionCreate(
                name="Holidays",
                source_type="ical",
                source_url="https://example.com/feed.ics",
            ),
        )
        assert result.name == "Holidays"


class TestUpdateEvent:
    @pytest.mark.asyncio
    async def test_only_organizer_can_update(self, service: EventService, repo: AsyncMock) -> None:
        event = _make_event()
        repo.get_by_id.return_value = event
        with pytest.raises(AuthorizationError):
            await service.update_event(event.id, uuid.uuid4(), EventUpdate(title="Hijack"))


class TestReminderOffsets:
    @pytest.mark.asyncio
    async def test_event_created_with_default_reminder_offset(
        self, service: EventService, repo: AsyncMock
    ) -> None:
        """Event creation with no offsets specified should use default [60]."""
        user_id = uuid.uuid4()

        def _fill(e: Event) -> Event:
            e.id = uuid.uuid4()
            e.created_at = datetime.now(UTC)
            e.updated_at = datetime.now(UTC)
            return e

        repo.create.side_effect = _fill
        data = EventCreate(
            title="Meeting",
            starts_at=datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
            ends_at=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
        )
        await service.create_event(user_id, data)
        # Verify that repo.create was called with reminder_offsets_minutes=[60]
        call_args = repo.create.call_args
        assert call_args is not None
        created_event = call_args[0][0]
        assert created_event.reminder_offsets_minutes == [60]

    @pytest.mark.asyncio
    async def test_event_created_with_custom_offsets(
        self, service: EventService, repo: AsyncMock
    ) -> None:
        """Event creation with custom offsets should persist them sorted."""
        user_id = uuid.uuid4()

        def _fill(e: Event) -> Event:
            e.id = uuid.uuid4()
            e.created_at = datetime.now(UTC)
            e.updated_at = datetime.now(UTC)
            return e

        repo.create.side_effect = _fill
        data = EventCreate(
            title="Deadline",
            starts_at=datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
            ends_at=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
            reminder_offsets_minutes=[1440, 15],  # Unsorted
        )
        await service.create_event(user_id, data)
        call_args = repo.create.call_args
        assert call_args is not None
        created_event = call_args[0][0]
        # Should be sorted and deduplicated
        assert created_event.reminder_offsets_minutes == [15, 1440]

    def test_invalid_offset_rejected(self) -> None:
        """Offsets not in {15, 60, 1440} should raise validation error."""
        from pydantic_core import ValidationError

        with pytest.raises(ValidationError, match="reminder_offsets_minutes"):
            EventCreate(
                title="Bad offset",
                starts_at=datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
                ends_at=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
                reminder_offsets_minutes=[999],  # Invalid
            )

    @pytest.mark.asyncio
    async def test_event_updated_with_offsets(
        self, service: EventService, repo: AsyncMock
    ) -> None:
        """Event update with custom offsets should persist them."""
        event = _make_event()
        event.reminder_offsets_minutes = [60]
        repo.get_by_id.return_value = event
        repo.update.return_value = event

        user_id = event.author_id
        update_data = EventUpdate(reminder_offsets_minutes=[15, 60])
        await service.update_event(event.id, user_id, update_data)

        # Verify update was called with the offsets
        repo.update.assert_awaited_once()
        call_args = repo.update.call_args
        assert call_args is not None
        assert call_args[0][1].get("reminder_offsets_minutes") == [15, 60]


class TestIcalToken:
    """@brief Tests for iCal token issuance and feed serving."""

    @pytest.fixture
    def token_repo(self) -> AsyncMock:
        """@brief Mock CalendarTokenRepository."""
        return AsyncMock(spec=CalendarTokenRepository)

    @pytest.mark.asyncio
    async def test_issue_ical_token_returns_raw_and_url(
        self, service: EventService, token_repo: AsyncMock
    ) -> None:
        """@brief issue_ical_token returns (raw, url) where url includes token."""
        user_id = uuid.uuid4()
        raw_token = "test_token_value_123"
        token_model = MagicMock(spec=CalendarToken)
        token_model.id = uuid.uuid4()
        token_model.user_id = user_id
        token_model.token_hash = "hashed"

        token_repo.issue.return_value = (raw_token, token_model)
        service._token_repo = token_repo

        raw, url = await service.issue_ical_token(user_id)

        assert raw == raw_token
        assert "feed.ics" in url
        assert raw_token in url
        assert "token=" in url
        token_repo.issue.assert_awaited_once_with(user_id=user_id, scope="ical")

    @pytest.mark.asyncio
    async def test_serve_ical_for_token_returns_ical_text(
        self, service: EventService, token_repo: AsyncMock, repo: AsyncMock
    ) -> None:
        """@brief serve_ical_for_token verifies token, fetches user events, returns iCal."""
        user_id = uuid.uuid4()
        raw_token = "valid_token"
        token_model = MagicMock(spec=CalendarToken)
        token_model.user_id = user_id

        token_repo.verify.return_value = token_model
        event = _make_event(author_id=user_id)
        repo.list_in_range.return_value = [event]

        service._token_repo = token_repo
        service._repo = repo

        ical_bytes = await service.serve_ical_for_token(raw_token)

        assert b"BEGIN:VCALENDAR" in ical_bytes
        assert b"BEGIN:VEVENT" in ical_bytes
        token_repo.verify.assert_awaited_once_with(raw_token)
        repo.list_in_range.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_serve_ical_for_invalid_token_raises(
        self, service: EventService, token_repo: AsyncMock
    ) -> None:
        """@brief serve_ical_for_token raises AuthorizationError for invalid token."""
        raw_token = "invalid_token"
        token_repo.verify.return_value = None

        service._token_repo = token_repo

        with pytest.raises(AuthorizationError):
            await service.serve_ical_for_token(raw_token)
