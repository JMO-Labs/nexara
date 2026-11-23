"""
@file test_presence_repo.py
@brief Real-Postgres privacy rules for presence lookups.
"""

from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.moderation import UserBlock
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.presence_repo import PresenceRepository
from app.services.presence_service import PresenceService

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
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


async def _user(s: AsyncSession, cid: uuid.UUID) -> User:
    tag = uuid.uuid4().hex[:8]
    u = User(community_id=cid, email=f"p_{tag}@x.dev", username=f"p_{tag}", display_name="p")
    s.add(u)
    await s.flush()
    return u


async def test_presence_privacy_rules(session: AsyncSession) -> None:
    c1, c2 = (
        Community(name=f"p1-{uuid.uuid4().hex[:6]}"),
        Community(name=f"p2-{uuid.uuid4().hex[:6]}"),
    )
    session.add_all([c1, c2])
    await session.flush()
    a, b, c = await _user(session, c1.id), await _user(session, c1.id), await _user(session, c1.id)
    d = await _user(session, c2.id)
    session.add(UserSettings(user_id=b.id, community_id=c1.id, show_online_status=False))
    session.add(UserBlock(community_id=c1.id, blocker_id=a.id, blocked_id=c.id))
    await session.flush()

    everyone = {a.id, b.id, c.id, d.id}
    with patch("app.services.presence_service.online_among", new=AsyncMock(return_value=everyone)):
        res = await PresenceService(PresenceRepository(session), c1.id).lookup(
            a.id, [a.id, b.id, c.id, d.id]
        )
    assert set(res.online) == {a.id}  # self; B hidden; C blocked; D other community
    assert c.id not in res.last_seen and d.id not in res.last_seen
    assert b.id in res.last_seen
