"""
@file test_passkey_repo_pg.py
@brief Real-Postgres tests for PasskeyRepository: conditional touch and duplicate add.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.passkey import Passkey
from app.models.user import User
from app.repositories.passkey_repo import PasskeyRepository

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
async def session():
    """@brief Transactional session rolled back after each test."""
    engine = create_async_engine(DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _setup(session: AsyncSession, count: int = 0) -> tuple[PasskeyRepository, Passkey]:
    tag = uuid.uuid4().hex[:8]
    u = User(community_id=CID, email=f"pk_{tag}@nexara.dev", username=f"pk_{tag}", display_name="p")
    session.add(u)
    await session.flush()
    repo = PasskeyRepository(session, CID)
    pk = await repo.add(
        Passkey(user_id=u.id, credential_id=os.urandom(16), public_key=b"k", sign_count=count)
    )
    return repo, pk


async def _stored(session: AsyncSession, pk: Passkey) -> int:
    stmt = select(Passkey.sign_count).where(Passkey.id == pk.id)
    return int((await session.execute(stmt)).scalar_one())


async def test_touch_advances_and_rejects_regression(session):
    repo, pk = await _setup(session, count=5)
    assert await repo.touch(pk, 6) is True
    assert await _stored(session, pk) == 6 and pk.last_used_at is not None
    assert await repo.touch(pk, 6) is False  # equal = replay
    assert await repo.touch(pk, 3) is False  # regression
    assert await repo.touch(pk, 0) is False  # stored > 0, assertion 0
    assert await _stored(session, pk) == 6


async def test_touch_allows_both_zero(session):
    repo, pk = await _setup(session, count=0)
    assert await repo.touch(pk, 0) is True
    assert await repo.touch(pk, 0) is True
    assert await _stored(session, pk) == 0


async def test_count_for_user(session):
    repo, pk = await _setup(session)
    assert await repo.count_for_user(pk.user_id) == 1
    assert await PasskeyRepository(session, uuid.uuid4()).count_for_user(pk.user_id) == 0


async def test_duplicate_credential_rolls_back_savepoint_only(session):
    repo, pk = await _setup(session)
    dup = Passkey(user_id=pk.user_id, credential_id=pk.credential_id, public_key=b"x")
    with pytest.raises(IntegrityError):
        await repo.add(dup)
    # Session still usable: the outer transaction survived the failed savepoint.
    assert await repo.count_for_user(pk.user_id) == 1
    other = await repo.add(
        Passkey(user_id=pk.user_id, credential_id=os.urandom(16), public_key=b"y")
    )
    assert other.id is not None
    assert await repo.count_for_user(pk.user_id) == 2
