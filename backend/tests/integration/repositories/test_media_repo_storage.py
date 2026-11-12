"""
@file test_media_repo_storage.py
@brief Real-Postgres tests for MediaRepository.get_user_storage_by_type.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.media import Media
from app.models.user import User
from app.repositories.media_repo import MediaRepository

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


async def _user(session: AsyncSession, suffix: str, community_id=COMMUNITY_ID) -> User:
    user = User(
        community_id=community_id,
        email=f"media_{suffix}@nexara.dev",
        username=f"media_{suffix}",
        display_name=suffix,
    )
    session.add(user)
    await session.flush()
    return user


def _media(user: User, content_type: str, size: int, community_id=COMMUNITY_ID) -> Media:
    key = uuid.uuid4().hex
    return Media(
        uploader_id=user.id,
        community_id=community_id,
        filename=key,
        content_type=content_type,
        storage_key=key,
        size_bytes=size,
        status="ready",
    )


class TestStorageByTypeIntegration:
    """@brief Category mapping and uploader/community scoping."""

    async def test_mapping_and_scoping(self, session: AsyncSession):
        me = await _user(session, uuid.uuid4().hex[:8])
        other = await _user(session, uuid.uuid4().hex[:8])
        other_comm = Community(name=f"c-{uuid.uuid4().hex[:8]}")
        session.add(other_comm)
        await session.flush()
        foreign = await _user(session, uuid.uuid4().hex[:8], other_comm.id)

        rows = [
            (me, "image/png", 1),
            (me, "image/jpeg", 2),
            (me, "video/mp4", 10),
            (me, "application/pdf", 100),
            (me, "application/msword", 200),
            (me, "text/plain", 400),
            (me, "application/vnd.ms-excel", 800),
            (me, "application/zip", 1000),
            (me, "audio/mpeg", 2000),
            # excluded: other uploader, other community
            (other, "image/png", 5000),
            (other, "application/zip", 5000),
        ]
        session.add_all([_media(u, ct, n) for u, ct, n in rows])
        session.add(_media(foreign, "image/png", 7000, other_comm.id))
        await session.flush()

        out = await MediaRepository(session).get_user_storage_by_type(me.id, COMMUNITY_ID)
        assert out == {"photos": 3, "videos": 10, "documents": 1500, "other": 3000}

    async def test_no_rows_returns_zeros(self, session: AsyncSession):
        me = await _user(session, uuid.uuid4().hex[:8])
        out = await MediaRepository(session).get_user_storage_by_type(me.id, COMMUNITY_ID)
        assert out == {"photos": 0, "videos": 0, "documents": 0, "other": 0}
