"""
@file test_user_repo_first_user.py
@brief Real-Postgres tests for UserRepository.is_first_user (admin bootstrap guard).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.user import User
from app.repositories.user_repo import UserRepository

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


async def _community(session: AsyncSession) -> Community:
    c = Community(name=f"fu-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    return c


async def _user(session: AsyncSession, community_id: uuid.UUID, **kw: object) -> User:
    tag = uuid.uuid4().hex[:6]
    u = User(
        community_id=community_id,
        email=f"fu_{tag}@nexara.dev",
        username=f"fu_{tag}",
        display_name="fu",
        **kw,
    )
    session.add(u)
    await session.flush()
    return u


async def test_empty_community_is_first(session):
    c = await _community(session)
    assert await UserRepository(session).is_first_user(c.id) is True


async def test_deleted_inactive_users_still_count(session):
    c = await _community(session)
    await _user(session, c.id, is_active=False, deleted_at=datetime.now(UTC))
    assert await UserRepository(session).is_first_user(c.id) is False


async def test_other_community_users_do_not_count(session):
    c1, c2 = await _community(session), await _community(session)
    await _user(session, c1.id)
    assert await UserRepository(session).is_first_user(c2.id) is True
