"""
@file test_trip_service.py
@brief Unit tests for TripService (AsyncMock repos).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, NotFoundError
from app.models.community import Community
from app.models.trip import Trip
from app.repositories.community_repo import CommunityRepository
from app.repositories.trip_repo import TripRepository
from app.schemas.trip import TripCreate
from app.services.trip_service import TripService
from tests.unit.services.strict_notify import strict_notify

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ME, W1, W2, STRANGER = (uuid.uuid4() for _ in range(4))


def _trip(user: uuid.UUID = ME, **kw) -> MagicMock:
    t = MagicMock(spec=Trip)
    t.id, t.user_id, t.label = uuid.uuid4(), user, "Drive home"
    t.expected_at = datetime.now(UTC) + timedelta(hours=1)
    t.arrived_at = t.ended_at = t.alerted_at = None
    for k, v in kw.items():
        setattr(t, k, v)
    return t


@pytest.fixture
def svc():
    repo = AsyncMock(spec=TripRepository)
    comm = AsyncMock(spec=CommunityRepository)
    community = MagicMock(spec=Community)
    community.features = {}
    comm.get.return_value = community
    repo.eligible_user_ids.side_effect = lambda ids, *_: set(ids)
    repo.names.return_value = {ME: "Ruth"}
    repo.watcher_ids.return_value = [W1, W2]
    notif = strict_notify()
    return TripService(repo, comm, notif, CID), repo, community, notif


def _body(minutes: int = 60, watchers=None) -> TripCreate:
    return TripCreate(
        label="Drive home",
        expected_at=datetime.now(UTC) + timedelta(minutes=minutes),
        watcher_ids=watchers or [W1, W2],
    )


async def test_start_notifies_watchers(svc) -> None:
    s, repo, _, notif = svc
    repo.create.return_value = _trip()
    await s.start(ME, _body())
    assert {c.args[0] for c in notif.notify.await_args_list} == {W1, W2}
    assert notif.notify.await_args_list[0].args[1] == "trip_started"


async def test_start_in_five_minutes_is_422(svc) -> None:
    s, repo, _, _ = svc
    with pytest.raises(AppError) as e:
        await s.start(ME, _body(minutes=5))
    assert e.value.status_code == 422
    repo.create.assert_not_awaited()


async def test_start_beyond_72h_is_422(svc) -> None:
    with pytest.raises(AppError) as e:
        await svc[0].start(ME, _body(minutes=72 * 60 + 5))
    assert e.value.status_code == 422


async def test_start_ineligible_watcher_is_422(svc) -> None:
    s, repo, _, _ = svc
    repo.eligible_user_ids.side_effect = lambda ids, *_: {W1}
    with pytest.raises(AppError) as e:
        await s.start(ME, _body())
    assert e.value.status_code == 422


async def test_second_active_trip_is_409(svc) -> None:
    s, repo, _, notif = svc
    repo.create.return_value = None
    with pytest.raises(AppError) as e:
        await s.start(ME, _body())
    assert e.value.status_code == 409
    notif.notify.assert_not_awaited()


async def test_feature_off_is_404(svc) -> None:
    s, _, community, _ = svc
    community.features = {"safe_arrival": False}
    with pytest.raises(AppError) as e:
        await s.start(ME, _body())
    assert e.value.status_code == 404


async def test_arrive_notifies_only_eligible_watchers(svc) -> None:
    s, repo, _, notif = svc
    trip = _trip()
    repo.get.return_value = trip
    repo.eligible_user_ids.side_effect = lambda ids, *_: {W1}  # W2 now blocked
    await s.arrive(trip.id, ME)
    assert trip.arrived_at is not None
    assert [c.args[:2] for c in notif.notify.await_args_list] == [(W1, "trip_arrived")]


async def test_only_traveler_can_arrive(svc) -> None:
    s, repo, _, _ = svc
    repo.get.return_value = _trip()
    with pytest.raises(NotFoundError):
        await s.arrive(uuid.uuid4(), W1)


async def test_extend_clears_alert(svc) -> None:
    s, repo, _, _ = svc
    trip = _trip(alerted_at=datetime.now(UTC))
    repo.get.return_value = trip
    await s.extend(trip.id, ME, datetime.now(UTC) + timedelta(hours=2))
    assert trip.alerted_at is None


async def test_extend_ended_trip_is_409(svc) -> None:
    s, repo, _, _ = svc
    repo.get.return_value = _trip(ended_at=datetime.now(UTC))
    with pytest.raises(AppError) as e:
        await s.extend(uuid.uuid4(), ME, datetime.now(UTC) + timedelta(hours=2))
    assert e.value.status_code == 409


async def test_stranger_gets_404(svc) -> None:
    s, repo, _, _ = svc
    repo.get.return_value = _trip()
    repo.is_watcher.return_value = False
    with pytest.raises(NotFoundError):
        await s.get(uuid.uuid4(), STRANGER)


async def test_blocked_watcher_gets_404(svc) -> None:
    s, repo, _, _ = svc
    repo.get.return_value = _trip()
    repo.is_watcher.return_value = True
    repo.eligible_user_ids.side_effect = lambda ids, *_: set()
    with pytest.raises(NotFoundError):
        await s.get(uuid.uuid4(), W1)


async def test_watcher_sees_trip_without_watcher_list(svc) -> None:
    s, repo, _, _ = svc
    repo.get.return_value = _trip()
    repo.is_watcher.return_value = True
    out = await s.get(uuid.uuid4(), W1)
    assert out.watchers == []


async def test_sweep_alerts_each_claimed_trip(svc) -> None:
    s, repo, _, notif = svc
    repo.claim_overdue.return_value = [_trip()]
    repo.end_stale.return_value = 2
    out = await s.sweep(datetime.now(UTC))
    assert out == {"alerted": 1, "ended": 2}
    assert [c.args[1] for c in notif.notify.await_args_list] == ["trip_overdue"] * 2


def test_overdue_type_not_digested_and_defaults_on() -> None:
    import app.services.notifications.types  # noqa: F401
    from app.services.notifications import registry

    t = registry.get("trip_overdue")
    assert t.group_window_seconds is None and t.toast_on_arrival and not t.digestable
    assert t.default_channels["inapp"] and t.default_channels["push"]
