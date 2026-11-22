"""
@file test_celebration_memorials.py
@brief Real-Postgres: remembrance entries only reveal a birthday that was
       shared with the community.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.celebration_repo import CelebrationRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _user(s: AsyncSession, name: str, *, shown: str | None = None) -> User:
    sfx = uuid.uuid4().hex[:6]
    u = User(
        community_id=CID, email=f"cm_{name}_{sfx}@nexara.dev", username=f"cm_{name}_{sfx}",
        display_name=name, birthday=date(1931, 3, 4), passed_on=date(2026, 1, 2),
        memorialized_at=datetime.now(UTC),
    )  # fmt: skip
    s.add(u)
    await s.flush()
    if shown:
        s.add(UserSettings(user_id=u.id, show_birthday_to=shown))
        await s.flush()
    return u


async def test_unshared_birthday_hidden(session: AsyncSession) -> None:
    viewer = await _user(session, "viewer")
    private = await _user(session, "private", shown="only_me")
    public = await _user(session, "public", shown="community")
    rows = {
        r[0]: r for r in await CelebrationRepository(session).memorialized_users(CID, viewer.id)
    }
    assert rows[private.id][3] is None and rows[private.id][4] == date(2026, 1, 2)
    assert rows[public.id][3] == date(1931, 3, 4)
