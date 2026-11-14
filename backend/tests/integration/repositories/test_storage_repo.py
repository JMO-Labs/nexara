"""
@file test_storage_repo.py
@brief Real-Postgres tests for StorageRepository.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.retention import StorageSnapshot
from app.models.user import User
from app.repositories.storage_repo import StorageRepository

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


async def _user(session: AsyncSession, used: int, *, deleted: bool = False, cid=COMMUNITY_ID):
    key = uuid.uuid4().hex[:12]
    user = User(
        community_id=cid,
        email=f"st_{key}@nexara.dev",
        username=f"st_{key}",
        display_name=key,
        storage_used=used,
        deleted_at=datetime.now(UTC) if deleted else None,
    )
    session.add(user)
    await session.flush()
    return user


async def _other_community(session: AsyncSession) -> uuid.UUID:
    community = Community(id=uuid.uuid4(), name=f"other-{uuid.uuid4().hex[:6]}")
    session.add(community)
    await session.flush()
    return community.id


async def test_snapshots_since_filters_and_orders(session):
    today = date.today()
    for offset in (40, 3, 1):
        session.add(
            StorageSnapshot(snapshot_date=today - timedelta(days=offset), total_bytes=offset)
        )
    await session.flush()
    got = await StorageRepository(session).snapshots_since(30)
    assert [s.total_bytes for s in got if s.total_bytes in (40, 3, 1)] == [3, 1]


async def test_top_users_orders_limits_and_scopes(session):
    other = await _other_community(session)
    big = await _user(session, 9_000_000_000)
    mid = await _user(session, 8_999_999_000)
    await _user(session, 9_500_000_000, deleted=True)
    await _user(session, 9_900_000_000, cid=other)
    got = await StorageRepository(session).top_users(COMMUNITY_ID, 2)
    assert [u.id for u in got] == [big.id, mid.id]


async def test_user_page_returns_page_and_total(session):
    repo = StorageRepository(session)
    _, before = await repo.user_page(COMMUNITY_ID, offset=0, limit=1)
    a = await _user(session, 9_100_000_000)
    b = await _user(session, 9_000_000_000)
    await _user(session, 1, deleted=True)
    first, total = await repo.user_page(COMMUNITY_ID, offset=0, limit=1)
    second, _ = await repo.user_page(COMMUNITY_ID, offset=1, limit=1)
    assert total == before + 2
    assert first[0].id == a.id
    assert second[0].id == b.id


async def test_total_user_bytes_sums_active_community_only(session):
    repo = StorageRepository(session)
    before = await repo.total_user_bytes(COMMUNITY_ID)
    other = await _other_community(session)
    await _user(session, 100)
    await _user(session, 50)
    await _user(session, 1000, deleted=True)
    await _user(session, 7000, cid=other)
    assert await repo.total_user_bytes(COMMUNITY_ID) == before + 150
    assert await repo.total_user_bytes(other) == 7000
