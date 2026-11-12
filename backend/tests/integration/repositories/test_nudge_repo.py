"""
@file test_nudge_repo.py
@brief Real-Postgres tests: NudgeRepository candidate, rate-limit and block queries.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.community import Community
from app.models.moderation import UserBlock
from app.models.nudge import Nudge
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.nudge_repo import NudgeRepository

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


async def _user(
    session: AsyncSession,
    *,
    days_ago: float | None = 15,
    opted_in: bool = True,
    community_id: uuid.UUID = COMMUNITY_ID,
) -> User:
    tag = uuid.uuid4().hex[:8]
    u = User(
        community_id=community_id,
        email=f"nu_{tag}@nexara.dev",
        username=f"nu_{tag}",
        display_name="n",
        last_seen_at=None if days_ago is None else datetime.now(UTC) - timedelta(days=days_ago),
    )
    session.add(u)
    await session.flush()
    session.add(
        UserSettings(user_id=u.id, community_id=community_id, receive_gentle_nudges=opted_in)
    )
    await session.flush()
    return u


async def _nudge(
    session: AsyncSession, sender: User, target: User, kind: str, age: timedelta
) -> None:
    session.add(
        Nudge(
            community_id=COMMUNITY_ID,
            sender_id=sender.id,
            target_id=target.id,
            nudge_type=kind,
            created_at=datetime.now(UTC) - age,
        )
    )
    await session.flush()


async def test_inactive_opted_in_user_is_candidate(session: AsyncSession) -> None:
    u = await _user(session, days_ago=15)
    assert u.id in await NudgeRepository(session).find_gentle_candidates(COMMUNITY_ID)


async def test_recently_active_user_not_candidate(session: AsyncSession) -> None:
    u = await _user(session, days_ago=13)
    assert u.id not in await NudgeRepository(session).find_gentle_candidates(COMMUNITY_ID)


async def test_opted_out_user_not_candidate(session: AsyncSession) -> None:
    u = await _user(session, days_ago=15, opted_in=False)
    assert u.id not in await NudgeRepository(session).find_gentle_candidates(COMMUNITY_ID)


async def test_gentle_cooldown_7_days(session: AsyncSession) -> None:
    recent = await _user(session)
    old = await _user(session)
    await _nudge(session, recent, recent, "gentle", timedelta(days=3))
    await _nudge(session, old, old, "gentle", timedelta(days=8))
    ids = await NudgeRepository(session).find_gentle_candidates(COMMUNITY_ID)
    assert recent.id not in ids
    assert old.id in ids


async def test_other_community_not_candidate(session: AsyncSession) -> None:
    other = Community(name="Other")
    session.add(other)
    await session.flush()
    u = await _user(session, community_id=other.id)
    assert u.id not in await NudgeRepository(session).find_gentle_candidates(COMMUNITY_ID)


async def test_rate_limit_window(session: AsyncSession) -> None:
    repo = NudgeRepository(session)
    s, t_in, t_out = [await _user(session) for _ in range(3)]
    await _nudge(session, s, t_in, "user_initiated", timedelta(hours=23))
    await _nudge(session, s, t_out, "user_initiated", timedelta(hours=25))
    assert await repo.has_recent_user_nudge(s.id, t_in.id, COMMUNITY_ID) is True
    assert await repo.has_recent_user_nudge(s.id, t_out.id, COMMUNITY_ID) is False


async def test_gentle_nudge_not_counted_for_rate_limit(session: AsyncSession) -> None:
    s, t = await _user(session), await _user(session)
    await _nudge(session, s, t, "gentle", timedelta(hours=1))
    assert await NudgeRepository(session).has_recent_user_nudge(s.id, t.id, COMMUNITY_ID) is False


async def test_blocked_both_directions(session: AsyncSession) -> None:
    repo = NudgeRepository(session)
    a, b, c = [await _user(session) for _ in range(3)]
    session.add(UserBlock(blocker_id=a.id, blocked_id=b.id, community_id=COMMUNITY_ID))
    await session.flush()
    assert await repo.is_blocked(a.id, b.id, COMMUNITY_ID) is True
    assert await repo.is_blocked(b.id, a.id, COMMUNITY_ID) is True
    assert await repo.is_blocked(a.id, c.id, COMMUNITY_ID) is False
