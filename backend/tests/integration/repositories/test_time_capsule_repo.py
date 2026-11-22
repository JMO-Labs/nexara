"""
@file test_time_capsule_repo.py
@brief Real-Postgres tests: audience resolution, atomic open claim, sealed media.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.household import HouseholdMember
from app.models.user import User
from app.repositories.moderation_repo import ModerationRepository
from app.repositories.time_capsule_repo import TimeCapsuleRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


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


async def _user(s: AsyncSession, name: str) -> User:
    u = User(
        community_id=CID,
        email=f"tc_{name}_{uuid.uuid4().hex[:6]}@nexara.dev",
        username=f"tc_{name}_{uuid.uuid4().hex[:6]}",
        display_name=name,
    )
    s.add(u)
    await s.flush()
    return u


async def test_open_due_claims_once_and_resolves_audience(session: AsyncSession) -> None:
    repo = TimeCapsuleRepository(session)
    ruth, maya, owner, blocked = [await _user(session, n) for n in ("ruth", "maya", "own", "blk")]
    pet = HouseholdMember(community_id=CID, owner_id=owner.id, kind="pet", name="Rex")
    session.add(pet)
    await session.flush()
    await ModerationRepository(session).create_block(ruth.id, blocked.id, CID)
    past = datetime.now(UTC) - timedelta(minutes=1)
    media = uuid.uuid4()
    cap = await repo.create(
        CID,
        ruth.id,
        title="t",
        body="b",
        media_ids=[media],
        open_at=past,
        recipients=[
            ("user", maya.id),
            ("household", pet.id),
            ("user", blocked.id),
            ("user", ruth.id),
        ],
    )
    assert await repo.is_sealed_media(media, CID, maya.id) is True
    assert await repo.is_sealed_media(media, CID, None) is True
    assert await repo.is_sealed_media(media, CID, ruth.id) is False
    assert await repo.is_recipient(cap.id, owner.id, CID) is True
    claimed = await repo.claim_due(datetime.now(UTC))
    assert [c.id for c in claimed] == [cap.id]
    assert await repo.claim_due(datetime.now(UTC)) == []
    assert await repo.resolve_user_ids(claimed[0]) == {maya.id, owner.id}
    assert await repo.is_sealed_media(media, CID, maya.id) is False
