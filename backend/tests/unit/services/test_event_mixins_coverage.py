"""
@file test_event_mixins_coverage.py
@brief Coverage tests for event RSVP, recurrence and subscription mixins (nexara#359).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.event import EventAttendance
from app.repositories.activity_repo import ActivityRepository
from app.repositories.event_repo import EventRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.schemas.event import CalendarSubscriptionUpdate, ContributionClaim, RSVPRequest
from app.services import event_recurrence
from app.services.event_service import EventService
from tests.unit.services.test_event_service import COMMUNITY_ID, _make_event


def _att(user_id: uuid.UUID, event_id: uuid.UUID) -> MagicMock:
    att = MagicMock(spec=EventAttendance)
    att.id = uuid.uuid4()
    att.event_id = event_id
    att.user_id = user_id
    att.status = "attending"
    att.note = None
    att.responded_at = datetime.now(UTC)
    return att


@pytest.fixture
def repo() -> AsyncMock:
    r = AsyncMock(spec=EventRepository)
    r.get_by_id.return_value = None
    return r


@pytest.fixture
def session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def notifications() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def activity_repo() -> AsyncMock:
    return AsyncMock(spec=ActivityRepository)


@pytest.fixture
def service(
    repo: AsyncMock, session: AsyncMock, notifications: AsyncMock, activity_repo: AsyncMock
) -> EventService:
    sg = AsyncMock(spec=SubgroupRepository)
    return EventService(
        event_repo=repo,
        community_id=COMMUNITY_ID,
        session=session,
        actor_id=uuid.uuid4(),
        notification_service=notifications,
        activity_repo=activity_repo,
        subgroup_repo=sg,
    )


def _slot(claimed_by: list[uuid.UUID] | None = None) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "title": "Salad",
        "quantity_needed": 3,
        "quantity_claimed": len(claimed_by or []),
        "claimed_by": [str(u) for u in (claimed_by or [])],
    }


class TestRsvpNotifyAndActivity:
    async def test_actor_name_falls_back_when_user_missing(
        self, service: EventService, session: AsyncMock
    ) -> None:
        session.get.return_value = None
        assert await service._actor_name(uuid.uuid4()) == "Someone"

    async def test_actor_name_uses_display_name(
        self, service: EventService, session: AsyncMock
    ) -> None:
        session.get.return_value = MagicMock(display_name="Ann")
        assert await service._actor_name(uuid.uuid4()) == "Ann"

    async def test_rsvp_forbidden_for_private_event(
        self, service: EventService, repo: AsyncMock
    ) -> None:
        repo.get_by_id.return_value = _make_event(visibility="private")
        with pytest.raises(AuthorizationError):
            await service.rsvp(uuid.uuid4(), uuid.uuid4(), RSVPRequest(status="attending"))

    async def test_rsvp_notifies_author_and_records_activity(
        self,
        service: EventService,
        repo: AsyncMock,
        session: AsyncMock,
        notifications: AsyncMock,
    ) -> None:
        event = _make_event()
        user_id = uuid.uuid4()
        repo.get_by_id.return_value = event
        repo.upsert_attendance.return_value = _att(user_id, event.id)
        session.get.return_value = MagicMock(display_name="Ann")
        found = MagicMock()
        found.scalar_one_or_none.return_value = MagicMock(display_name="Ann")
        session.execute.return_value = found

        with patch("app.services.event_rsvp.record_activity", new=AsyncMock()) as rec:
            await service.rsvp(event.id, user_id, RSVPRequest(status="attending"))

        notifications.notify.assert_awaited_once()
        assert notifications.notify.await_args.kwargs["type"] == "event_rsvp"
        assert rec.await_args.kwargs["metadata"]["actor_name"] == "Ann"

    async def test_rsvp_activity_unknown_user_and_notify_failure_swallowed(
        self,
        service: EventService,
        repo: AsyncMock,
        session: AsyncMock,
        notifications: AsyncMock,
    ) -> None:
        event = _make_event()
        user_id = uuid.uuid4()
        repo.get_by_id.return_value = event
        repo.upsert_attendance.return_value = _att(user_id, event.id)
        notifications.notify.side_effect = RuntimeError("boom")
        session.get.return_value = None
        missing = MagicMock()
        missing.scalar_one_or_none.return_value = None
        session.execute.return_value = missing

        with patch("app.services.event_rsvp.record_activity", new=AsyncMock()) as rec:
            result = await service.rsvp(event.id, user_id, RSVPRequest(status="attending"))

        assert result.status == "attending"
        assert rec.await_args.kwargs["metadata"]["actor_name"] == "Unknown"


class TestListAndCancelRsvp:
    async def test_list_rsvps_not_found(self, service: EventService) -> None:
        with pytest.raises(NotFoundError):
            await service.list_rsvps(uuid.uuid4(), uuid.uuid4())

    async def test_list_rsvps_forbidden(self, service: EventService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = _make_event(visibility="private")
        with pytest.raises(AuthorizationError):
            await service.list_rsvps(uuid.uuid4(), uuid.uuid4())

    async def test_list_rsvps_returns_records(self, service: EventService, repo: AsyncMock) -> None:
        event = _make_event()
        repo.get_by_id.return_value = event
        repo.list_attendance.return_value = [_att(uuid.uuid4(), event.id)]
        out = await service.list_rsvps(event.id, uuid.uuid4())
        assert len(out) == 1

    async def test_cancel_rsvp_not_found(self, service: EventService) -> None:
        with pytest.raises(NotFoundError):
            await service.cancel_rsvp(uuid.uuid4(), uuid.uuid4())

    async def test_cancel_rsvp_removes_attendance(
        self, service: EventService, repo: AsyncMock
    ) -> None:
        event = _make_event()
        repo.get_by_id.return_value = event
        uid = uuid.uuid4()
        await service.cancel_rsvp(event.id, uid)
        repo.remove_attendance.assert_awaited_once_with(event.id, uid)


class TestContributionGuards:
    async def test_claim_event_not_found(self, service: EventService) -> None:
        with pytest.raises(NotFoundError):
            await service.claim_contribution(
                uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), ContributionClaim(quantity=1)
            )

    async def test_claim_forbidden(self, service: EventService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = _make_event(visibility="private")
        with pytest.raises(AuthorizationError):
            await service.claim_contribution(
                uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), ContributionClaim(quantity=1)
            )

    async def test_claim_slot_not_found(self, service: EventService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = _make_event(contribution_slots=[_slot()])
        with pytest.raises(NotFoundError):
            await service.claim_contribution(
                uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), ContributionClaim(quantity=1)
            )

    async def test_unclaim_event_not_found(self, service: EventService) -> None:
        with pytest.raises(NotFoundError):
            await service.unclaim_contribution(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

    async def test_unclaim_slot_not_found(self, service: EventService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = _make_event(contribution_slots=[_slot()])
        with pytest.raises(NotFoundError):
            await service.unclaim_contribution(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

    async def test_unclaim_removes_claimer(
        self, service: EventService, repo: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        uid = uuid.uuid4()
        slot = _slot([uid])
        event = _make_event(contribution_slots=[slot])
        repo.get_by_id.return_value = event
        repo.update.return_value = event
        build = AsyncMock(return_value="resp")
        monkeypatch.setattr(service, "_build_response", build)

        out = await service.unclaim_contribution(event.id, uuid.UUID(slot["id"]), uid)

        assert out == "resp"
        saved = repo.update.await_args.args[1]["contribution_slots"][0]
        assert saved["quantity_claimed"] == 0
        assert saved["claimed_by"] == []

    async def test_unclaim_noop_when_not_claimer(
        self, service: EventService, repo: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        other = uuid.uuid4()
        slot = _slot([other])
        event = _make_event(contribution_slots=[slot])
        repo.get_by_id.return_value = event
        repo.update.return_value = event
        monkeypatch.setattr(service, "_build_response", AsyncMock())

        await service.unclaim_contribution(event.id, uuid.UUID(slot["id"]), uuid.uuid4())

        saved = repo.update.await_args.args[1]["contribution_slots"][0]
        assert saved["quantity_claimed"] == 1


class TestRecurrenceExpansion:
    def test_non_recurring_returns_single_occurrence(self, service: EventService) -> None:
        event = _make_event()
        out = service.expand_occurrences(event, event.starts_at, event.ends_at)
        assert len(out) == 1
        assert out[0].starts_at == event.starts_at

    def test_invalid_rrule_returns_empty(self, service: EventService) -> None:
        event = _make_event(recurrence_rule="FREQ=NOPE")
        assert service.expand_occurrences(event, event.starts_at, event.ends_at) == []

    def test_occurrences_capped(
        self, service: EventService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(event_recurrence, "MAX_OCCURRENCES", 3)
        event = _make_event(recurrence_rule="FREQ=DAILY")
        out = service.expand_occurrences(
            event, event.starts_at, event.starts_at + timedelta(days=30)
        )
        assert len(out) == 3

    def test_append_until_strips_count_and_handles_trailing_semicolon(
        self, service: EventService
    ) -> None:
        assert (
            service._append_until("FREQ=WEEKLY;", "20260508T175959Z")
            == "FREQ=WEEKLY;UNTIL=20260508T175959Z"
        )
        assert (
            service._append_until("FREQ=WEEKLY;COUNT=4", "20260508T175959Z")
            == "FREQ=WEEKLY;UNTIL=20260508T175959Z"
        )


class TestSubscriptionNotFound:
    async def test_delete_subscription_not_found(
        self, service: EventService, repo: AsyncMock
    ) -> None:
        repo.get_subscription.return_value = None
        with pytest.raises(NotFoundError):
            await service.delete_subscription(uuid.uuid4(), uuid.uuid4())
        repo.delete_subscription.assert_not_awaited()

    async def test_update_subscription_not_found(
        self, service: EventService, repo: AsyncMock
    ) -> None:
        repo.get_subscription.return_value = None
        with pytest.raises(NotFoundError):
            await service.update_subscription(
                uuid.uuid4(), uuid.uuid4(), CalendarSubscriptionUpdate(name="x")
            )
