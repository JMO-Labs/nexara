"""
@file test_subgroup_member_previews.py
@brief Real-Postgres tests: batched member previews and counts for the subgroup list.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.subgroup_member_repo import SubgroupMemberRepository

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


async def _user(session: AsyncSession, *, deleted: bool = False) -> User:
    tag = uuid.uuid4().hex[:8]
    u = User(
        community_id=COMMUNITY_ID,
        email=f"sp_{tag}@nexara.dev",
        username=f"sp_{tag}",
        display_name=f"Person {tag}",
        avatar_url=f"https://cdn.test/{tag}.png",
        deleted_at=datetime.now(UTC) if deleted else None,
    )
    session.add(u)
    await session.flush()
    return u


async def _group(session: AsyncSession, name: str) -> Subgroup:
    sg = Subgroup(
        community_id=COMMUNITY_ID,
        name=name,
        slug=f"sp-{uuid.uuid4().hex[:10]}",
    )
    session.add(sg)
    await session.flush()
    return sg


async def _join(session: AsyncSession, sg: Subgroup, users: list[User]) -> None:
    for u in users:
        session.add(SubgroupMember(community_id=COMMUNITY_ID, subgroup_id=sg.id, user_id=u.id))
    await session.flush()


async def test_previews_capped_at_four_and_counts_per_group(session: AsyncSession) -> None:
    big = await _group(session, "big")
    small = await _group(session, "small")
    empty = await _group(session, "empty")
    await _join(session, big, [await _user(session) for _ in range(6)])
    await _join(session, small, [await _user(session) for _ in range(2)])
    repo = SubgroupMemberRepository(session)
    ids = [big.id, small.id, empty.id]

    previews = await repo.list_member_previews(COMMUNITY_ID, ids, limit=4)
    counts = await repo.count_members_bulk(COMMUNITY_ID, ids)

    assert len(previews[big.id]) == 4
    assert len(previews[small.id]) == 2
    assert previews.get(empty.id, []) == []
    assert counts == {big.id: 6, small.id: 2, empty.id: 0}
    first = previews[big.id][0]
    assert set(first) == {"id", "display_name", "avatar_url"}
    assert first["avatar_url"].startswith("https://cdn.test/")


async def test_previews_exclude_deleted_users(session: AsyncSession) -> None:
    sg = await _group(session, "mixed")
    active = [await _user(session) for _ in range(2)]
    gone = await _user(session, deleted=True)
    await _join(session, sg, [*active, gone])
    repo = SubgroupMemberRepository(session)

    previews = await repo.list_member_previews(COMMUNITY_ID, [sg.id], limit=4)

    assert {p["id"] for p in previews[sg.id]} == {u.id for u in active}
