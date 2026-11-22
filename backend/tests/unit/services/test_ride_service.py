"""
@file test_ride_service.py
@brief Unit tests for RideService (AsyncMock repos).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.models.community import Community
from app.models.event import Event
from app.models.event_ride import EventRide
from app.repositories.community_repo import CommunityRepository
from app.repositories.event_repo import EventRepository
from app.repositories.ride_repo import RideRepository
from app.schemas.ride import RideCreate
from app.services.event_service import EventService
from app.services.ride_service import RideService
from tests.unit.services.strict_notify import strict_notify

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DRIVER, MAYA, RUTH, VIEWER = (uuid.uuid4() for _ in range(4))


def _ride(kind="offer", owner=DRIVER, seats=2) -> MagicMock:
    r = MagicMock(spec=EventRide)
    r.id, r.event_id, r.community_id = uuid.uuid4(), EVENT_ID, CID
    r.kind, r.user_id, r.seats = kind, owner, seats
    r.origin, r.note, r.depart_at = "Elm St", "", datetime(2026, 12, 1, 15, tzinfo=UTC)
    r.created_at, r.deleted_at = datetime.now(UTC), None
    return r


EVENT_ID = uuid.uuid4()


@pytest.fixture
def svc():
    repo = AsyncMock(spec=RideRepository)
    events = AsyncMock(spec=EventRepository)
    es = AsyncMock(spec=EventService)
    comm = AsyncMock(spec=CommunityRepository)
    community = MagicMock(spec=Community)
    community.features = {}
    comm.get.return_value = community
    event = MagicMock(spec=Event)
    event.id, event.title = EVENT_ID, "BBQ"
    events.get_by_id.return_value = event
    es._can_view.return_value = True
    repo.blocked_with.return_value = set()
    repo.memorialized.return_value = False
    repo.riding.return_value = False
    repo.passenger_ids.return_value = []
    repo.seats_taken.return_value = 0
    repo.passengers_for.return_value = []
    repo.names.return_value = {DRIVER: "Dee", MAYA: "Maya", RUTH: "Ruth"}
    notif = strict_notify()
    s = RideService(repo, events, es, comm, notif, CID)
    return s, repo, es, community, notif


async def test_list_hidden_event_is_404(svc) -> None:
    s, repo, es, *_ = svc
    es._can_view.return_value = False
    with pytest.raises(NotFoundError):
        await s.list_for_event(EVENT_ID, VIEWER)
    repo.list_for_event.assert_not_awaited()


async def test_offer_hidden_event_is_404(svc) -> None:
    s, repo, es, *_ = svc
    es._can_view.return_value = False
    with pytest.raises(NotFoundError):
        await s.offer(EVENT_ID, DRIVER, RideCreate(seats=2))
    repo.create.assert_not_awaited()


async def test_feature_off_is_404(svc) -> None:
    s, _r, _e, community, _n = svc
    community.features = {"rides": False}
    with pytest.raises(AppError) as e:
        await s.list_for_event(EVENT_ID, VIEWER)
    assert e.value.status_code == 404


async def test_memorialized_cannot_offer_or_join(svc) -> None:
    s, repo, *_ = svc
    repo.memorialized.return_value = True
    with pytest.raises(AuthorizationError):
        await s.offer(EVENT_ID, DRIVER, RideCreate(seats=2))
    repo.get.return_value = _ride()
    with pytest.raises(AuthorizationError):
        await s.join(uuid.uuid4(), MAYA)


async def test_join_full_is_409(svc) -> None:
    s, repo, *_ = svc
    repo.get.return_value = _ride(seats=1)
    repo.seats_taken.return_value = 1
    with pytest.raises(AppError) as e:
        await s.join(uuid.uuid4(), MAYA)
    assert (e.value.status_code, e.value.code) == (409, "RIDE_FULL")
    repo.get.assert_awaited_with(repo.get.await_args.args[0], CID, lock=True)


async def test_join_second_ride_is_409(svc) -> None:
    s, repo, *_ = svc
    repo.get.return_value = _ride()
    repo.riding.return_value = True
    with pytest.raises(AppError) as e:
        await s.join(uuid.uuid4(), MAYA)
    assert (e.value.status_code, e.value.code) == (409, "ALREADY_RIDING")


async def test_join_own_ride_rejected(svc) -> None:
    s, repo, *_ = svc
    repo.get.return_value = _ride()
    with pytest.raises(AppError) as e:
        await s.join(uuid.uuid4(), DRIVER)
    assert e.value.status_code == 422


async def test_join_blocked_driver_is_404(svc) -> None:
    s, repo, *_ = svc
    repo.get.return_value = _ride()
    repo.blocked_with.return_value = {DRIVER}
    with pytest.raises(NotFoundError):
        await s.join(uuid.uuid4(), MAYA)
    repo.add_passenger.assert_not_awaited()


async def test_join_notifies_driver(svc) -> None:
    s, repo, _e, _c, notif = svc
    repo.get.return_value = _ride()
    await s.join(uuid.uuid4(), MAYA)
    repo.add_passenger.assert_awaited_once()
    assert notif.notify.await_args.args[:2] == (DRIVER, "ride_update")


async def test_cancel_notifies_two_passengers(svc) -> None:
    s, repo, _e, _c, notif = svc
    repo.get.return_value = _ride()
    repo.passenger_ids.return_value = [MAYA, RUTH]
    await s.cancel(uuid.uuid4(), DRIVER)
    assert {c.args[0] for c in notif.notify.await_args_list} == {MAYA, RUTH}
    repo.soft_delete.assert_awaited_once()


async def test_cancel_skips_blocked_and_unviewing_passengers(svc) -> None:
    s, repo, es, _c, notif = svc
    repo.get.return_value = _ride()
    repo.passenger_ids.return_value = [MAYA, RUTH]
    repo.blocked_with.return_value = {MAYA}
    await s.cancel(uuid.uuid4(), DRIVER)
    assert [c.args[0] for c in notif.notify.await_args_list] == [RUTH]


async def test_cancel_by_non_owner_forbidden(svc) -> None:
    s, repo, *_ = svc
    repo.get.return_value = _ride()
    with pytest.raises(AuthorizationError):
        await s.cancel(uuid.uuid4(), MAYA)


async def test_answer_request_adds_requester_and_closes(svc) -> None:
    s, repo, _e, _c, notif = svc
    offer, req = _ride(), _ride("request", MAYA, 1)
    repo.get.side_effect = [offer, req]
    await s.answer_request(req.id, offer.id, DRIVER)
    repo.add_passenger.assert_awaited_once_with(offer.id, MAYA, 1)
    repo.soft_delete.assert_awaited_once_with(req)
    assert notif.notify.await_args.args[0] == MAYA


async def test_answer_with_someone_elses_offer_forbidden(svc) -> None:
    s, repo, *_ = svc
    offer, req = _ride(owner=RUTH), _ride("request", MAYA, 1)
    repo.get.side_effect = [offer, req]
    with pytest.raises(AuthorizationError):
        await s.answer_request(req.id, offer.id, DRIVER)


async def test_list_hides_blocked_passengers_and_computes_seats(svc) -> None:
    s, repo, *_ = svc
    ride = _ride(seats=3)
    p1, p2 = MagicMock(), MagicMock()
    p1.ride_id = p2.ride_id = ride.id
    p1.user_id, p2.user_id = MAYA, RUTH
    p1.seats = p2.seats = 1
    repo.list_for_event.return_value = [ride]
    repo.passengers_for.return_value = [p1, p2]
    repo.blocked_with.return_value = {RUTH}
    [out] = await s.list_for_event(EVENT_ID, VIEWER)
    assert out.seats_left == 1
    assert [p.user_id for p in out.passengers] == [MAYA]


def test_depart_at_normalised_to_utc() -> None:
    naive = RideCreate(seats=1, depart_at=datetime(2026, 12, 1, 9, 0))
    assert naive.depart_at is not None and naive.depart_at.tzinfo is UTC
    with pytest.raises(ValueError):
        RideCreate(seats=9)


async def test_join_multiple_seats_checks_capacity(svc) -> None:
    s, repo, *_ = svc
    repo.get.return_value = _ride(seats=3)
    repo.seats_taken.return_value = 2
    with pytest.raises(AppError) as e:
        await s.join(uuid.uuid4(), MAYA, 2)
    assert (e.value.status_code, e.value.code) == (409, "RIDE_FULL")
    await s.join(uuid.uuid4(), MAYA, 1)
    repo.add_passenger.assert_awaited_once_with(repo.get.return_value.id, MAYA, 1)


async def test_answer_three_seat_request_into_two_seat_offer_is_409(svc) -> None:
    s, repo, *_ = svc
    offer, req = _ride(seats=2), _ride("request", MAYA, 3)
    repo.get.side_effect = [offer, req]
    repo.seats_taken.return_value = 0
    with pytest.raises(AppError) as e:
        await s.answer_request(req.id, offer.id, DRIVER)
    assert (e.value.status_code, e.value.code) == (409, "RIDE_FULL")
    repo.add_passenger.assert_not_awaited()
    repo.soft_delete.assert_not_awaited()


async def test_answer_three_seat_request_into_four_seat_offer_leaves_one(svc) -> None:
    s, repo, *_ = svc
    offer, req = _ride(seats=4), _ride("request", MAYA, 3)
    repo.get.side_effect = [offer, req]
    p = MagicMock()
    p.ride_id, p.user_id, p.seats = offer.id, MAYA, 3
    repo.passengers_for.return_value = [p]
    out = await s.answer_request(req.id, offer.id, DRIVER)
    repo.add_passenger.assert_awaited_once_with(offer.id, MAYA, 3)
    assert out.seats_left == 1
    assert out.passengers[0].seats == 3
