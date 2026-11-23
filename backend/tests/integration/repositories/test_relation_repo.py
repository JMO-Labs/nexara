"""
@file test_relation_repo.py
@brief Real-Postgres tests: pair uniqueness in both directions and
       visibility/block handling of list_for.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.exceptions import NotFoundError
from app.models.household import HouseholdMember
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.household_repo import HouseholdRepository
from app.repositories.moderation_repo import ModerationRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.profile_repo import ProfileRepository
from app.repositories.relation_repo import RelationRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.notification_service import NotificationService
from app.services.relation_service import RelationService

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
        email=f"rl_{name}_{uuid.uuid4().hex[:6]}@nexara.dev",
        username=f"rl_{name}_{uuid.uuid4().hex[:6]}",
        display_name=name,
    )
    s.add(u)
    await s.flush()
    return u


def _svc(s: AsyncSession) -> RelationService:
    notif = NotificationService(NotificationRepository(s), SettingsRepository(s), CID)
    return RelationService(
        RelationRepository(s),
        ProfileRepository(s),
        HouseholdRepository(s),
        CommunityRepository(s),
        notif,
        CID,
    )


async def test_pair_unique_in_both_directions(session: AsyncSession) -> None:
    repo = RelationRepository(session)
    a, b = await _user(session, "a"), await _user(session, "b")
    f = {"community_id": CID, "kind": "parent", "created_by": a.id, "status": "pending"}
    assert await repo.create(from_user_id=a.id, to_user_id=b.id, **f) is not None
    assert await repo.create(from_user_id=b.id, to_user_id=a.id, **f) is None
    assert await repo.create(from_user_id=a.id, to_user_id=b.id, **f) is None
    assert await repo.pair_exists(CID, b.id, user_id=a.id) is True


async def test_household_pair_unique_and_check_one_target(session: AsyncSession) -> None:
    repo = RelationRepository(session)
    a = await _user(session, "a")
    m = HouseholdMember(community_id=CID, owner_id=a.id, kind="person", name="Gran")
    session.add(m)
    await session.flush()
    f = {"community_id": CID, "kind": "parent", "created_by": a.id, "status": "confirmed"}
    assert await repo.create(from_user_id=a.id, to_household_member_id=m.id, **f) is not None
    assert await repo.create(from_user_id=a.id, to_household_member_id=m.id, **f) is None
    assert await repo.create(from_user_id=a.id, **f) is None  # no target violates the check


async def test_list_for_visibility_and_blocks(session: AsyncSession) -> None:
    svc = _svc(session)
    ruth, dana, maya, blk = [await _user(session, n) for n in ("ruth", "dana", "maya", "blk")]
    await svc.request(dana, to_user_id=ruth.id, kind="parent")
    await svc.confirm((await svc.requests(ruth))[0].id, ruth)
    out = await svc.list_for(ruth.id, maya)
    assert [(r.person.name, r.display) for r in out] == [("dana", "child")]
    # pending requests are visible to the parties only
    await svc.request(maya, to_user_id=ruth.id, kind="friend")
    assert len(await svc.list_for(ruth.id, blk)) == 1
    assert len(await svc.list_for(ruth.id, ruth)) == 2
    # a blocked pair cannot see each other's list
    await ModerationRepository(session).create_block(blk.id, ruth.id, CID)
    with pytest.raises(NotFoundError):
        await svc.list_for(ruth.id, blk)
    # the other person being blocked drops them from the list
    await ModerationRepository(session).create_block(maya.id, dana.id, CID)
    assert await svc.list_for(ruth.id, maya) == []
    # private level hides the list from everyone else
    repo = SettingsRepository(session)
    await repo.get_or_create(ruth.id, CID)
    await repo.update(ruth.id, {"field_visibility": {"relations": "private"}})
    assert await svc.list_for(ruth.id, dana) == []
    assert len(await svc.list_for(ruth.id, ruth)) == 2
