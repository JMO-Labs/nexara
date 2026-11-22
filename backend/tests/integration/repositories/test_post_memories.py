"""
@file test_post_memories.py
@brief Real-Postgres tests for PostMemoriesRepository.on_this_day visibility.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.moderation import UserBlock
from app.models.post import Post
from app.models.subgroup import Subgroup
from app.models.user import User
from app.repositories.post_memories_repo import PostMemoriesRepository

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
        community_id=CID, email=f"mem_{name}_{sfx}@nexara.dev", username=f"m_{name}_{sfx}",
        display_name=name,
    )  # fmt: skip
    s.add(u)
    await s.flush()
    return u


async def _post(s, author, when, *, visibility="community", subgroup_id=None, deleted=False):
    p = Post(
        community_id=CID, author_id=author.id, content="x", visibility=visibility,
        subgroup_id=subgroup_id, created_at=when,
        deleted_at=datetime.now(UTC) if deleted else None,
    )  # fmt: skip
    s.add(p)
    await s.flush()
    return p


async def _ids(s, viewer, tz="UTC"):
    repo = PostMemoriesRepository(s)
    items = await repo.on_this_day(CID, viewer.id, 11, 22, 2026, tz=tz)
    return {i["id"] for i in items}


async def test_visibility_matrix(session: AsyncSession):
    ruth, maya, blocked = await _user(session, "ruth"), await _user(session, "maya"), None
    blocked = await _user(session, "blocked")
    sg = Subgroup(community_id=CID, name="Left", slug=f"left-{uuid.uuid4().hex[:6]}")
    session.add(sg)
    await session.flush()
    session.add(UserBlock(community_id=CID, blocker_id=maya.id, blocked_id=blocked.id))
    await session.flush()
    t = datetime(2025, 11, 22, 12, tzinfo=UTC)
    ok = await _post(session, ruth, t)
    current = await _post(session, ruth, datetime(2026, 11, 22, 12, tzinfo=UTC))
    left = await _post(session, ruth, t, visibility="subgroup", subgroup_id=sg.id)
    blk = await _post(session, blocked, t)
    dele = await _post(session, ruth, t, deleted=True)
    other_day = await _post(session, ruth, datetime(2025, 11, 21, 12, tzinfo=UTC))
    got = await _ids(session, maya)
    assert str(ok.id) in got
    for p in (current, left, blk, dele, other_day):
        assert str(p.id) not in got


async def test_local_timezone_shifts_day(session: AsyncSession):
    ruth, maya = await _user(session, "ruth"), await _user(session, "maya")
    late = await _post(session, ruth, datetime(2025, 11, 23, 2, 0, tzinfo=UTC))
    assert str(late.id) not in await _ids(session, maya, "UTC")
    assert str(late.id) in await _ids(session, maya, "Pacific/Honolulu")


async def test_newest_year_first(session: AsyncSession):
    ruth, maya = await _user(session, "ruth"), await _user(session, "maya")
    old = await _post(session, ruth, datetime(2020, 11, 22, 12, tzinfo=UTC))
    new = await _post(session, ruth, datetime(2025, 11, 22, 12, tzinfo=UTC))
    items = await PostMemoriesRepository(session).on_this_day(CID, maya.id, 11, 22, 2026)
    assert [i["id"] for i in items] == [str(new.id), str(old.id)]
