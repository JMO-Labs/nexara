"""
@file test_two_factor_policy_pg.py
@brief Real-Postgres tests: require_2fa grace clocks start only when a member becomes covered.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.user import User
from app.repositories.two_factor_repo import TwoFactorRepository
from app.repositories.user_repo import UserRepository
from app.services.admin_service import AdminService
from app.services.auth.policy import setup_claims

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
WEEK = 7 * 24 * 3600


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


async def _user(session: AsyncSession, role: str, since: datetime | None = None) -> User:
    tag = uuid.uuid4().hex[:8]
    u = User(
        community_id=CID,
        email=f"tp_{tag}@nexara.dev",
        username=f"tp_{tag}",
        display_name="t",
        role=role,
        password_hash="h",
        two_factor_required_since=since,
    )
    session.add(u)
    await session.flush()
    return u


async def _since(session: AsyncSession, u: User) -> datetime | None:
    stmt = select(User.two_factor_required_since).where(User.id == u.id)
    return (await session.execute(stmt)).scalar_one()


async def test_admins_policy_stamps_only_admins(session):
    repo = TwoFactorRepository(session)
    admin, member = await _user(session, "admin"), await _user(session, "member")
    await repo.set_policy(CID, "admins")
    assert await _since(session, admin) is not None
    assert await _since(session, member) is None


async def test_widen_then_narrow(session):
    repo = TwoFactorRepository(session)
    old = datetime.now(UTC) - timedelta(days=3)
    admin, member = await _user(session, "admin", old), await _user(session, "member")
    await repo.set_policy(CID, "everyone")
    assert await _since(session, member) is not None
    assert await _since(session, admin) == old  # existing clock kept
    await repo.set_policy(CID, "admins")
    assert await _since(session, member) is None  # no longer covered
    assert await _since(session, admin) == old


async def test_promoted_member_gets_fresh_grace(session):
    repo = TwoFactorRepository(session)
    await repo.set_policy(CID, "admins")
    # Stale stamp left over (e.g. an earlier "everyone" period 10 days ago).
    member = await _user(session, "member", datetime.now(UTC) - timedelta(days=10))
    actor = await _user(session, "admin")
    svc = AdminService(
        session=session,
        user_repo=UserRepository(session),
        audit_repo=AsyncMock(),
        community_id=CID,
        settings=MagicMock(),
    )
    await svc.change_role(actor, member.id, "admin", None)
    claims = await setup_claims(session, member)
    assert claims["twofa_setup_required"] is True
    assert claims["grace_until"] >= time.time() + WEEK - 60


async def test_demoted_admin_clock_cleared(session):
    repo = TwoFactorRepository(session)
    admin, actor = await _user(session, "admin"), await _user(session, "admin")
    await repo.set_policy(CID, "admins")
    assert await _since(session, admin) is not None
    svc = AdminService(
        session=session,
        user_repo=UserRepository(session),
        audit_repo=AsyncMock(),
        community_id=CID,
        settings=MagicMock(),
    )
    await svc.change_role(actor, admin.id, "member", None)
    assert await _since(session, admin) is None
    assert await setup_claims(session, admin) == {}
