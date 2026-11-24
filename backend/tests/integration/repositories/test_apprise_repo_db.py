"""
@file test_apprise_repo_db.py
@brief Real-Postgres: member vs admin Apprise rows never mix; allow_local round-trips.
"""

from __future__ import annotations

import os
import uuid

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.user import User
from app.repositories.apprise_repo import AppriseRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture(autouse=True)
def _key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPRISE_ENCRYPTION_KEY", Fernet.generate_key().decode())


@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _user(s: AsyncSession) -> User:
    sfx = uuid.uuid4().hex[:6]
    u = User(
        community_id=CID, email=f"ap_{sfx}@nexara.dev", username=f"ap_{sfx}", display_name="ap"
    )  # fmt: skip
    s.add(u)
    await s.flush()
    return u


async def test_member_and_admin_rows_are_separated(session: AsyncSession) -> None:
    repo = AppriseRepository(session)
    user = await _user(session)
    member = await repo.create(CID, user.id, "ntfy://ntfy.sh/member", "m")
    admin = await repo.create(CID, None, "ntfy://ntfy.sh/admin", "a", is_admin_target=True)
    mine = await repo.list_for_user(user.id, CID, enabled_only=False)
    targets = await repo.list_admin_targets(CID, enabled_only=False)
    assert [r.id for r in mine] == [member.id]
    assert admin.id in [r.id for r in targets]
    assert member.id not in [r.id for r in targets]
    assert mine[0].apprise_url == "ntfy://ntfy.sh/member"


async def test_allow_local_round_trip(session: AsyncSession) -> None:
    repo = AppriseRepository(session)
    await repo.set_allow_local(CID, True)
    assert await repo.allow_local(CID) is True
    await repo.set_allow_local(CID, False)
    assert await repo.allow_local(CID) is False
