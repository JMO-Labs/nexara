"""
@file test_ride_repo.py
@brief Real-Postgres: two concurrent joins for the last seat (separate
       sessions) yield exactly one success and one 409 RIDE_FULL.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.exceptions import AppError
from app.models.event import Event
from app.models.event_ride import EventRide, RidePassenger
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.event_repo import EventRepository
from app.repositories.ride_repo import RideRepository
from app.services.event_service import EventService
from app.services.notification_service import NotificationService
from app.services.ride_service import RideService

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _service(s: AsyncSession) -> RideService:
    es = AsyncMock(spec=EventService)
    es._can_view.return_value = True
    notif = AsyncMock(spec=NotificationService)
    return RideService(
        RideRepository(s), EventRepository(s), es, CommunityRepository(s), notif, CID
    )


@pytest.fixture
async def factory():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


async def test_last_seat_race_one_winner(factory) -> None:
    sfx = uuid.uuid4().hex[:6]
    async with factory() as s, s.begin():
        users = []
        for n in ("drv", "a", "b"):
            u = User(
                community_id=CID, email=f"rr_{n}_{sfx}@nexara.dev",
                username=f"rr_{n}_{sfx}", display_name=n,
            )  # fmt: skip
            s.add(u)
            users.append(u)
        await s.flush()
        now = datetime.now(UTC) + timedelta(days=3)
        ev = Event(
            community_id=CID, author_id=users[0].id, title="BBQ", starts_at=now,
            ends_at=now + timedelta(hours=2), ical_uid=f"rr-{sfx}@nexara", visibility="community",
        )  # fmt: skip
        s.add(ev)
        await s.flush()
        ride = EventRide(
            community_id=CID, event_id=ev.id, kind="offer", user_id=users[0].id, seats=1
        )
        s.add(ride)
        await s.flush()
        ids = (users[0].id, users[1].id, users[2].id, ride.id, ev.id)
    drv, a, b, ride_id, ev_id = ids

    async def join(uid: uuid.UUID) -> object:
        async with factory() as sess:
            try:
                out = await _service(sess).join(ride_id, uid)
                await sess.commit()
                return out
            except AppError as e:
                await sess.rollback()
                return e

    try:
        results = await asyncio.gather(join(a), join(b))
        errs = [r for r in results if isinstance(r, AppError)]
        assert len(errs) == 1
        assert (errs[0].status_code, errs[0].code) == (409, "RIDE_FULL")
        async with factory() as s:
            n = await s.scalar(
                select(func.count())
                .select_from(RidePassenger)
                .where(RidePassenger.ride_id == ride_id)
            )
        assert n == 1
    finally:
        async with factory() as s, s.begin():
            await s.execute(delete(EventRide).where(EventRide.event_id == ev_id))
            await s.execute(delete(Event).where(Event.id == ev_id))
            await s.execute(delete(User).where(User.id.in_([drv, a, b])))
