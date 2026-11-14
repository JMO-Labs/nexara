"""
@file test_block_enforcement.py
@brief Real-Postgres tests: bidirectional block enforcement on feed and moderation repo.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.user import User
from app.repositories.moderation_repo import ModerationRepository
from app.repositories.post_repo import PostRepository

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
        email=f"be_{name}_{uuid.uuid4().hex[:6]}@nexara.dev",
        username=f"be_{name}_{uuid.uuid4().hex[:6]}",
        display_name=name,
    )
    session.add(u)
    await session.flush()
    return u


async def _feed_authors(repo: PostRepository, viewer: User) -> set[uuid.UUID]:
    rows, _ = await repo.list_feed(COMMUNITY_ID, viewer_id=viewer.id)
    return {uuid.UUID(r["author"]["id"]) for r in rows}


async def test_block_hides_content_for_both_users_and_unblock_restores(
    session: AsyncSession,
) -> None:
    posts = PostRepository(session)
    mod = ModerationRepository(session)
    a, b = await _user(session, "a"), await _user(session, "b")
    await posts.create_post(a.id, "from a", COMMUNITY_ID)
    await posts.create_post(b.id, "from b", COMMUNITY_ID)

    await mod.create_block(a.id, b.id, COMMUNITY_ID)

    assert b.id not in await _feed_authors(posts, a)
    assert a.id not in await _feed_authors(posts, b)

    await mod.remove_block(a.id, b.id)

    assert b.id in await _feed_authors(posts, a)
    assert a.id in await _feed_authors(posts, b)


async def test_is_blocked_either_is_symmetric(session: AsyncSession) -> None:
    mod = ModerationRepository(session)
    a, b, c = [await _user(session, n) for n in "abc"]
    await mod.create_block(a.id, b.id, COMMUNITY_ID)

    assert await mod.is_blocked_either(a.id, b.id)
    assert await mod.is_blocked_either(b.id, a.id)
    assert not await mod.is_blocked_either(a.id, c.id)


async def test_list_blocked_users_returns_only_own_blocks(session: AsyncSession) -> None:
    mod = ModerationRepository(session)
    a, b, c = [await _user(session, n) for n in "abc"]
    await mod.create_block(a.id, b.id, COMMUNITY_ID)
    await mod.create_block(c.id, a.id, COMMUNITY_ID)

    users = await mod.list_blocked_users(a.id, COMMUNITY_ID)

    assert [u.id for u in users] == [b.id]
