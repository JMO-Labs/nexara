"""
@file test_kudos_repo_block.py
@brief Real-Postgres tests: KudosRepository block filter and cursor validation.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.exceptions import AppError
from app.models.moderation import UserBlock
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
        email=f"kb_{name}_{uuid.uuid4().hex[:6]}@nexara.dev",
        username=f"kb_{name}_{uuid.uuid4().hex[:6]}",
        display_name=name,
    )
    session.add(u)
    await session.flush()
    return u


async def test_blocked_author_kudos_hidden(session: AsyncSession) -> None:
    repo = KudosRepository(session)
    viewer, blocked, friend, rcpt = [await _user(session, n) for n in "vbfr"]
    session.add(UserBlock(blocker_id=viewer.id, blocked_id=blocked.id, community_id=COMMUNITY_ID))
    await session.flush()
    await repo.create_kudos(blocked.id, rcpt.id, "bad", COMMUNITY_ID)
    await repo.create_kudos(friend.id, rcpt.id, "good", COMMUNITY_ID)

    rows, _ = await repo.list_kudos(COMMUNITY_ID, viewer.id)

    assert [p.content for p, _r in rows] == ["good"]


async def test_author_who_blocked_viewer_hidden(session: AsyncSession) -> None:
    repo = KudosRepository(session)
    viewer, author, rcpt = [await _user(session, n) for n in "var"]
    session.add(UserBlock(blocker_id=author.id, blocked_id=viewer.id, community_id=COMMUNITY_ID))
    await session.flush()
    await repo.create_kudos(author.id, rcpt.id, "hi", COMMUNITY_ID)

    rows, _ = await repo.list_kudos(COMMUNITY_ID, viewer.id)

    assert rows == []


async def test_malformed_cursor_raises_400(session: AsyncSession) -> None:
    repo = KudosRepository(session)
    viewer = await _user(session, "v")
    with pytest.raises(AppError) as exc:
        await repo.list_kudos(COMMUNITY_ID, viewer.id, cursor="not-a-date")
    assert exc.value.status_code == 400
    assert exc.value.code == "INVALID_CURSOR"
