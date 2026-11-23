"""
@file test_backup_code_db.py
@brief Real-Postgres: a backup code can be spent exactly once.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.security import hash_token
from app.models.auth import UserBackupCode
from app.models.user import User
from app.services.auth.totp_replay import consume_backup_code

URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
async def session():
    engine = create_async_engine(URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def test_second_consume_of_same_code_is_false(session: AsyncSession):
    sfx = uuid.uuid4().hex[:6]
    u = User(community_id=CID, email=f"bc_{sfx}@nexara.dev", username=f"bc_{sfx}", display_name="b")
    session.add(u)
    await session.flush()
    session.add(UserBackupCode(user_id=u.id, code_hash=hash_token("ABCD1234")))
    await session.flush()
    assert await consume_backup_code(session, u.id, "ABCD1234") is True
    assert await consume_backup_code(session, u.id, "ABCD1234") is False
    assert await consume_backup_code(session, u.id, "WRONG000") is False
