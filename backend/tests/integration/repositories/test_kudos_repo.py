"""
@file test_kudos_repo.py
@brief Real-Postgres tests: KudosRepository create, filters, pagination.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.kudos_repo import KudosRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)
COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
async def session():
    """@brief Transactional session rolled back after each test."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _user(session: AsyncSession, name: str) -> User:
    u = User(
        community_id=COMMUNITY_ID,
        email=f"k_{name}_{uuid.uuid4().hex[:6]}@nexara.dev",
        username=f"k_{name}_{uuid.uuid4().hex[:6]}",
        display_name=name,
    )
    session.add(u)
    await session.flush()
    return u


async def test_create_kudos_community_visibility(session: AsyncSession) -> None:
    repo = KudosRepository(session)
    a, r = await _user(session, "a"), await _user(session, "r")
    post = await repo.create_kudos(a.id, r.id, "nice", COMMUNITY_ID)
    assert post.visibility == "community"
    assert post.recipient_id == r.id


async def test_list_filters_by_recipient_and_returns_recipient(session: AsyncSession) -> None:
    repo = KudosRepository(session)
    a, r1, r2 = [await _user(session, n) for n in ("a", "r1", "r2")]
    await repo.create_kudos(a.id, r1.id, "one", COMMUNITY_ID)
    await repo.create_kudos(a.id, r2.id, "two", COMMUNITY_ID)
    rows, cursor = await repo.list_kudos(COMMUNITY_ID, a.id, recipient_id=r1.id)
    assert [(p.content, u.id) for p, u in rows] == [("one", r1.id)]
    assert cursor is None


async def test_subgroup_kudos_visible_only_to_members(session: AsyncSession) -> None:
    repo = KudosRepository(session)
    a, r, outsider = [await _user(session, n) for n in ("a", "r", "o")]
    slug = f"sg{uuid.uuid4().hex[:6]}"
    sg = Subgroup(community_id=COMMUNITY_ID, name=slug, slug=slug, created_by=a.id)
    session.add(sg)
    await session.flush()
    session.add(SubgroupMember(subgroup_id=sg.id, user_id=a.id))
    await session.flush()
    post = await repo.create_kudos(a.id, r.id, "private", COMMUNITY_ID, sg.id)
    assert post.visibility == "subgroup"
    member_rows, _c = await repo.list_kudos(COMMUNITY_ID, a.id)
    outsider_rows, _c = await repo.list_kudos(COMMUNITY_ID, outsider.id)
    assert [p.id for p, _u in member_rows] == [post.id]
    assert outsider_rows == []


async def test_pagination_cursor_and_soft_delete(session: AsyncSession) -> None:
    repo = KudosRepository(session)
    a, r = await _user(session, "a"), await _user(session, "r")
    now = datetime.now(UTC)
    posts = []
    for i in range(3):
        p = await repo.create_kudos(a.id, r.id, f"m{i}", COMMUNITY_ID)
        p.created_at = now - timedelta(minutes=i)
        posts.append(p)
    posts[2].deleted_at = now
    await session.flush()

    page1, cursor = await repo.list_kudos(COMMUNITY_ID, a.id, limit=1)
    assert [p.content for p, _u in page1] == ["m0"]
    assert cursor is not None
    page2, cursor2 = await repo.list_kudos(COMMUNITY_ID, a.id, cursor=cursor, limit=5)
    assert [p.content for p, _u in page2] == ["m1"]
    assert cursor2 is None
