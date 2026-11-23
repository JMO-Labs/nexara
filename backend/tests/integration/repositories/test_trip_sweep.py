"""
@file test_trip_sweep.py
@brief Real-Postgres: the overdue sweep alerts once, extend re-arms it, stale
       trips auto-end, flag-off communities are skipped, one active trip per user.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
import app.services.notifications.types  # noqa: F401
from app.models.community import Community
from app.models.moderation import UserBlock
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.trip_repo import TripRepository
from app.services.notification_service import NotificationService
from app.services.trip_service import TripService

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
T0 = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)


@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _user(s: AsyncSession, name: str, **kw) -> User:
    sfx = uuid.uuid4().hex[:6]
    u = User(
        community_id=CID, email=f"tr_{name}_{sfx}@nexara.dev", username=f"tr_{name}_{sfx}",
        display_name=name, **kw,
    )  # fmt: skip
    s.add(u)
    await s.flush()
    return u


def _svc(session: AsyncSession):
    notif = AsyncMock(spec=NotificationService)
    return TripService(TripRepository(session), CommunityRepository(session), notif, CID), notif


async def _trip(s: AsyncSession, expected: datetime, watchers: list[User], traveler: User):
    repo = TripRepository(s)
    trip = await repo.create(CID, traveler.id, "Home", expected, [w.id for w in watchers])
    assert trip is not None
    return trip


def _sent(notif: AsyncMock, kind: str) -> list[uuid.UUID]:
    return [c.args[0] for c in notif.notify.await_args_list if c.args[1] == kind]


async def test_sweep_alert_once_extend_rearms_auto_end(session: AsyncSession) -> None:
    me, w = await _user(session, "me"), await _user(session, "w")
    svc, notif = _svc(session)
    trip = await _trip(session, T0, [w], me)

    await svc.sweep(T0 + timedelta(minutes=30))  # inside grace
    assert _sent(notif, "trip_overdue") == []

    assert (await svc.sweep(T0 + timedelta(hours=1, minutes=1)))["alerted"] == 1
    assert (await svc.sweep(T0 + timedelta(hours=1, minutes=6)))["alerted"] == 0
    assert _sent(notif, "trip_overdue") == [w.id]

    now = datetime.now(UTC)
    await svc.extend(trip.id, me.id, now + timedelta(hours=1))
    assert trip.alerted_at is None
    await session.flush()
    assert (await svc.sweep(now + timedelta(hours=2, minutes=1)))["alerted"] == 1
    assert _sent(notif, "trip_overdue") == [w.id, w.id]

    out = await svc.sweep(now + timedelta(hours=25, minutes=1))
    assert out["ended"] == 1 and trip.ended_at is not None
    assert await TripRepository(session).active_for_user(me.id, CID) is None


async def test_sweep_skips_blocked_and_memorialized_watchers(session: AsyncSession) -> None:
    me = await _user(session, "me")
    ok, blocked, gone = (
        await _user(session, "ok"),
        await _user(session, "blocked"),
        await _user(session, "gone"),
    )
    await _trip(session, T0, [ok, blocked, gone], me)
    session.add(UserBlock(blocker_id=blocked.id, blocked_id=me.id, community_id=CID))
    gone.memorialized_at = T0
    await session.flush()
    svc, notif = _svc(session)
    await svc.sweep(T0 + timedelta(hours=2))
    assert _sent(notif, "trip_overdue") == [ok.id]


async def test_second_active_trip_rejected_by_index(session: AsyncSession) -> None:
    me, w = await _user(session, "me"), await _user(session, "w")
    await _trip(session, T0, [w], me)
    assert await TripRepository(session).create(CID, me.id, "Again", T0, [w.id]) is None


async def test_flag_off_community_not_alerted(session: AsyncSession) -> None:
    me, w = await _user(session, "me"), await _user(session, "w")
    await _trip(session, T0, [w], me)
    community = await session.get(Community, CID)
    community.features = {"safe_arrival": False}
    await session.flush()
    svc, notif = _svc(session)
    assert (await svc.sweep(T0 + timedelta(hours=2)))["alerted"] == 0
