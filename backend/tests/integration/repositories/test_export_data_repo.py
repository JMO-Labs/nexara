"""
@file test_export_data_repo.py
@brief Real-Postgres integration tests for ExportDataRepository.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.post import Post
from app.models.user import User
from app.repositories.export_data_repo import ExportDataRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)


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


async def _user(session: AsyncSession, community: Community) -> User:
    tag = uuid.uuid4().hex[:8]
    u = User(
        community_id=community.id,
        email=f"x_{tag}@nexara.dev",
        username=f"x_{tag}",
        display_name="x",
        password_hash="secret-hash",
        totp_secret="secret-totp",
    )
    session.add(u)
    await session.flush()
    return u


@pytest.fixture
async def world(session: AsyncSession):
    c = Community(name=f"exd-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    me, other = await _user(session, c), await _user(session, c)
    session.add_all(
        [
            Post(community_id=c.id, author_id=me.id, content="mine"),
            Post(community_id=c.id, author_id=other.id, content="theirs"),
        ]
    )
    await session.flush()
    return c, me, other


async def test_posts_only_for_user_and_community(session, world):
    c, me, _ = world
    rows = await ExportDataRepository(session).list_posts(me.id, c.id)
    assert [r["content"] for r in rows] == ["mine"]


async def test_posts_excluded_for_other_community(session, world):
    _, me, _ = world
    rows = await ExportDataRepository(session).list_posts(me.id, uuid.uuid4())
    assert rows == []


async def test_empty_sections_for_other_user_data(session, world):
    c, me, _ = world
    repo = ExportDataRepository(session)
    fns = (repo.list_comments, repo.list_reactions, repo.list_events, repo.list_rsvps)
    for fn in (*fns, repo.list_media):
        assert await fn(me.id, c.id) == []


async def test_profile_excludes_secrets(session, world):
    c, me, _ = world
    prof = await ExportDataRepository(session).get_profile(me.id, c.id)
    assert prof["id"] == str(me.id)
    assert "password_hash" not in prof and "totp_secret" not in prof


async def test_profile_wrong_community_raises(session, world):
    _, me, _ = world
    with pytest.raises(LookupError):
        await ExportDataRepository(session).get_profile(me.id, uuid.uuid4())
