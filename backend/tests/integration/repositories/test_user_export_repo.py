"""
@file test_user_export_repo.py
@brief Real-Postgres integration tests for UserExportRepository.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.user import User
from app.repositories.user_export_repo import UserExportRepository

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


@pytest.fixture
async def owner(session: AsyncSession) -> User:
    c = Community(name=f"exp-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    tag = uuid.uuid4().hex[:6]
    u = User(
        community_id=c.id,
        email=f"exp_{tag}@nexara.dev",
        username=f"exp_{tag}",
        display_name="exp",
    )
    session.add(u)
    await session.flush()
    return u


async def test_create_defaults_pending_with_created_at(session, owner):
    repo = UserExportRepository(session)
    row = await repo.create(owner.id, owner.community_id)
    assert row.id is not None
    assert row.status == "pending"
    assert row.created_at is not None
    assert row.ready_at is None and row.expires_at is None and row.file_key is None
    fetched = await repo.get_by_id(row.id, owner.community_id)
    assert fetched is not None and fetched.user_id == owner.id


async def test_get_by_id_scoped_to_community(session, owner):
    repo = UserExportRepository(session)
    row = await repo.create(owner.id, owner.community_id)
    assert await repo.get_by_id(row.id, uuid.uuid4()) is None


async def test_get_latest_by_user_orders_created_desc(session, owner):
    repo = UserExportRepository(session)
    older = await repo.create(owner.id, owner.community_id)
    newer = await repo.create(owner.id, owner.community_id)
    # Same transaction => same now(); set explicit, inverted timestamps.
    base = datetime.now(UTC)
    older.created_at = base - timedelta(days=2)
    newer.created_at = base - timedelta(days=1)
    await session.flush()
    latest = await repo.get_latest_by_user(owner.id, owner.community_id)
    assert latest is not None and latest.id == newer.id
    assert await repo.get_latest_by_user(owner.id, uuid.uuid4()) is None


async def test_update_status_persists_fields(session, owner):
    repo = UserExportRepository(session)
    row = await repo.create(owner.id, owner.community_id)
    ready = datetime.now(UTC).replace(microsecond=0)
    expires = ready + timedelta(hours=48)
    await repo.update_status(
        row.id,
        "ready",
        file_key="exports/x.zip",
        file_size_bytes=4096,
        ready_at=ready,
        expires_at=expires,
    )
    session.expunge_all()
    got = await repo.get_by_id(row.id, owner.community_id)
    assert got is not None
    assert got.status == "ready"
    assert got.file_key == "exports/x.zip"
    assert got.file_size_bytes == 4096
    assert got.ready_at == ready
    assert got.expires_at == expires


async def test_update_status_missing_raises(session):
    with pytest.raises(LookupError):
        await UserExportRepository(session).update_status(uuid.uuid4(), "failed")
