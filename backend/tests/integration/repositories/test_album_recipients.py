"""
@file test_album_recipients.py
@brief Real-Postgres: album reminders only reach attendees who can still see
       the event (group members, not blocked by/with the author).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.event import Event, EventAttendance
from app.models.moderation import UserBlock
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.album_repo import AlbumRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _user(s: AsyncSession, name: str) -> User:
    sfx = uuid.uuid4().hex[:6]
    u = User(
        community_id=CID, email=f"al_{name}_{sfx}@nexara.dev", username=f"al_{name}_{sfx}",
        display_name=name,
    )  # fmt: skip
    s.add(u)
    await s.flush()
    return u


async def _event(s: AsyncSession, author: User, **kw: object) -> Event:
    now = datetime.now(UTC)
    e = Event(
        community_id=CID, author_id=author.id, title="BBQ", starts_at=now - timedelta(hours=24),
        ends_at=now - timedelta(hours=20), ical_uid=f"{uuid.uuid4()}@t", **kw,
    )  # fmt: skip
    s.add(e)
    await s.flush()
    return e


async def _going(s: AsyncSession, e: Event, *users: User) -> None:
    for u in users:
        s.add(EventAttendance(community_id=CID, event_id=e.id, user_id=u.id, status="attending"))
    await s.flush()


async def test_group_event_skips_non_members_and_blocked(session: AsyncSession) -> None:
    ruth, maya, left, blocker = [await _user(session, n) for n in ("ruth", "maya", "left", "bl")]
    sg = Subgroup(community_id=CID, name="Fam", slug=f"fam-{uuid.uuid4().hex[:6]}")
    session.add(sg)
    await session.flush()
    for u in (ruth, maya, blocker):
        session.add(SubgroupMember(subgroup_id=sg.id, user_id=u.id))
    session.add(UserBlock(community_id=CID, blocker_id=blocker.id, blocked_id=ruth.id))
    await session.flush()
    e = await _event(session, ruth, visibility="subgroup", subgroup_id=sg.id)
    await _going(session, e, ruth, maya, left, blocker)
    got = set(await AlbumRepository(session).going_user_ids(e.id))
    assert got == {ruth.id, maya.id}


async def test_private_event_only_author(session: AsyncSession) -> None:
    ruth, maya = [await _user(session, n) for n in ("ruth", "maya")]
    e = await _event(session, ruth, visibility="private")
    await _going(session, e, ruth, maya)
    assert set(await AlbumRepository(session).going_user_ids(e.id)) == {ruth.id}
