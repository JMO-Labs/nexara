"""
@file test_retention_repo.py
@brief Real-Postgres integration tests for RetentionRepository.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.repositories.retention_repo import RetentionRepository

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


async def test_upsert_inserts_then_updates(session):
    repo = RetentionRepository(session)
    row = await repo.upsert("notifications", True, 30, False, None)
    assert row.retention_days == 30
    row = await repo.upsert("notifications", False, None, True, None)
    assert row.enabled is False
    assert row.retention_days is None
    assert row.delete_media_files is True
    rows = [r for r in await repo.list_all() if r.policy_key == "notifications"]
    assert len(rows) == 1
    assert rows[0].updated_at is not None
