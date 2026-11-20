"""
@file test_activity_repo_tz.py
@brief activity_events.created_at is timestamptz: the model must bind/return
       aware datetimes (an aware feed cursor 500'd /home/feed page 2).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.activity_event import ActivityEvent
from app.models.community import Community
from app.models.user import User
from app.repositories.activity_repo import ActivityRepository

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


async def _user(session: AsyncSession, cid: uuid.UUID) -> User:
    tag = uuid.uuid4().hex[:6]
    u = User(
        community_id=cid, email=f"tz_{tag}@nexara.dev", username=f"tz_{tag}", display_name="tz"
    )
    session.add(u)
    await session.flush()
    return u


async def test_aware_cursor_and_aware_results(session: AsyncSession) -> None:
    c = Community(name=f"tz-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    actor, viewer = await _user(session, c.id), await _user(session, c.id)
    session.add(
        ActivityEvent(
            community_id=c.id,
            actor_id=actor.id,
            verb="post.commented",
            object_type="post",
            object_id=uuid.uuid4(),
            visibility="community",
            event_metadata={},
            is_active=True,
        )
    )
    await session.flush()

    rows = await ActivityRepository(session).list_for_user(
        community_id=c.id,
        viewer_id=viewer.id,
        viewer_subgroup_ids=[],
        cursor=datetime.now(UTC) + timedelta(minutes=1),
        limit=10,
    )
    assert len(rows) == 1
    assert rows[0].created_at.tzinfo is not None
