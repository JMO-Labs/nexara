"""
@file test_sso_subgroup_sync.py
@brief Real-Postgres: SSO subgroup sync removes only source='sso' memberships.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.subgroup_member_repo import SubgroupMemberRepository
from app.services.oauth.group_mapper import sync_subgroups

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
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


async def _group(session: AsyncSession) -> Subgroup:
    sg = Subgroup(community_id=CID, name="g", slug=f"sso-{uuid.uuid4().hex[:10]}")
    session.add(sg)
    await session.flush()
    return sg


async def test_group_dropped_removes_sso_keeps_manual(session: AsyncSession):
    tag = uuid.uuid4().hex[:8]
    user = User(
        community_id=CID, email=f"sso_{tag}@nexara.dev", username=f"sso_{tag}", display_name="S"
    )
    session.add(user)
    await session.flush()
    kept, dropped, manual = await _group(session), await _group(session), await _group(session)
    session.add(SubgroupMember(community_id=CID, subgroup_id=manual.id, user_id=user.id))
    await session.flush()
    repo = SubgroupMemberRepository(session)

    await sync_subgroups(repo, CID, user.id, {kept.id: "member", dropped.id: "member"})
    assert set(await repo.list_sso_subgroup_ids(user.id, CID)) == {kept.id, dropped.id}

    await sync_subgroups(repo, CID, user.id, {kept.id: "moderator"})
    assert await repo.list_sso_subgroup_ids(user.id, CID) == [kept.id]
    row = await repo.get_membership(kept.id, user.id)
    assert row is not None and row.role == "moderator" and row.source == "sso"
    m = await repo.get_membership(manual.id, user.id)
    assert m is not None and m.source == "manual"


async def test_owner_lookups_include_soft_deleted(session: AsyncSession):
    """Unique email/username span soft-deleted rows; sync must not collide."""
    from datetime import UTC, datetime

    from app.repositories.user_repo import UserRepository

    tag = uuid.uuid4().hex[:8]
    gone = User(
        community_id=CID,
        email=f"Gone_{tag}@nexara.dev",
        username=f"Gone_{tag}",
        display_name="G",
        deleted_at=datetime.now(UTC),
    )
    session.add(gone)
    await session.flush()
    users = UserRepository(session)
    assert await users.find_by_email(f"gone_{tag}@nexara.dev") is None
    assert await users.email_owner_id(f"gone_{tag}@nexara.dev") == gone.id
    assert await users.username_owner_id(f"gone_{tag}") == gone.id
    assert await users.username_owner_id(f"free_{tag}") is None


async def test_try_create_savepoint_and_magic_link_revoke(session: AsyncSession):
    """Username race: unique violation returns None, outer txn stays usable."""
    from datetime import UTC, datetime, timedelta

    from app.models.auth import MagicLinkToken
    from app.repositories.token_repo import TokenRepository
    from app.repositories.user_repo import UserRepository

    tag = uuid.uuid4().hex[:8]
    users = UserRepository(session)

    def mk(email: str) -> User:
        return User(community_id=CID, email=email, username=f"race_{tag}", display_name="R")

    first = await users.try_create(mk(f"r1_{tag}@nexara.dev"))
    assert first is not None
    assert await users.try_create(mk(f"r2_{tag}@nexara.dev")) is None
    assert await users.username_owner_id(f"race_{tag}") == first.id  # txn still usable

    session.add(
        MagicLinkToken(
            user_id=first.id,
            token_hash=uuid.uuid4().hex,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
    )
    await session.flush()
    assert await TokenRepository(session).revoke_magic_links_for_user(first.id) == 1
