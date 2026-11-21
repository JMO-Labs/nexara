"""
@file test_chat_read_repo.py
@brief Real-Postgres integration tests for ChatReadRepository.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.chat import ChatMessage
from app.models.chat_read import ChatRead
from app.models.community import Community
from app.models.subgroup import ChatChannel
from app.models.user import User
from app.repositories.chat_read_repo import ChatReadRepository

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


async def _user(session, community_id, username):
    u = User(
        community_id=community_id,
        email=f"{username}_{uuid.uuid4().hex[:6]}@nexara.dev",
        username=username,
        display_name=username.title(),
    )
    session.add(u)
    await session.flush()
    return u


@pytest.fixture
async def world(session):
    c = Community(name=f"cr-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    ana = await _user(session, c.id, f"ana{uuid.uuid4().hex[:4]}")
    bob = await _user(session, c.id, f"bob{uuid.uuid4().hex[:4]}")
    ch = ChatChannel(community_id=c.id, name="general", channel_type="community")
    session.add(ch)
    await session.flush()
    return c, ana, bob, ch


async def _post(session, world, author, content, age):
    c, _, _, ch = world
    m = ChatMessage(
        community_id=c.id,
        channel_id=ch.id,
        author_id=author.id,
        content=content,
        created_at=datetime.now(UTC) - age,
    )
    session.add(m)
    await session.flush()
    return m


def _since():
    return datetime.now(UTC) - timedelta(days=7)


async def test_own_messages_not_unread(session, world):
    c, ana, _, ch = world
    await _post(session, world, ana, "mine", timedelta(minutes=1))
    stats = await ChatReadRepository(session).channel_stats(
        ana.id, ana.username, [ch.id], c.id, _since()
    )
    assert stats[ch.id].unread_count == 0
    assert stats[ch.id].last_message is not None


async def test_no_read_row_counts_only_last_7_days(session, world):
    c, ana, bob, ch = world
    await _post(session, world, bob, "ancient", timedelta(days=20))
    await _post(session, world, bob, "recent", timedelta(days=1))
    stats = await ChatReadRepository(session).channel_stats(
        ana.id, ana.username, [ch.id], c.id, _since()
    )
    assert stats[ch.id].unread_count == 1
    assert stats[ch.id].last_author_name == bob.display_name


async def test_read_row_overrides_default_window(session, world):
    c, ana, bob, ch = world
    await _post(session, world, bob, "one", timedelta(hours=5))
    await _post(session, world, bob, "two", timedelta(hours=1))
    repo = ChatReadRepository(session)
    await repo.mark_read(ana.id, ch.id, c.id, datetime.now(UTC) - timedelta(hours=2))
    stats = await repo.channel_stats(ana.id, ana.username, [ch.id], c.id, _since())
    assert stats[ch.id].unread_count == 1


async def test_mark_read_never_moves_backwards(session, world):
    c, ana, _, ch = world
    repo = ChatReadRepository(session)
    newer = datetime.now(UTC)
    await repo.mark_read(ana.id, ch.id, c.id, newer)
    await repo.mark_read(ana.id, ch.id, c.id, newer - timedelta(days=1))
    row = await session.get(ChatRead, (ana.id, ch.id))
    await session.refresh(row)
    assert row.last_read_at == newer


async def test_mention_matches_word_boundary(session, world):
    c, ana, bob, ch = world
    repo = ChatReadRepository(session)
    await _post(session, world, bob, f"Hi @{ana.username.title()}!", timedelta(minutes=2))
    stats = await repo.channel_stats(ana.id, ana.username, [ch.id], c.id, _since())
    assert stats[ch.id].mentions_me is True

    await _post(session, world, bob, f"yo @{ana.username}bel", timedelta(minutes=1))
    other = await repo.channel_stats(ana.id, ana.username + "x", [ch.id], c.id, _since())
    assert other[ch.id].mentions_me is False
