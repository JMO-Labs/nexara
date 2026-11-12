"""
@file test_birthday_repo.py
@brief Real-Postgres integration tests for BirthdayRepository.
"""

from __future__ import annotations

import os
import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.birthday_repo import BirthdayRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)

# A date unlikely to collide with seeded data.
MONTH, DAY = 7, 4
TODAY_BDAY = date(1990, MONTH, DAY)
OTHER_BDAY = date(1990, MONTH, DAY + 1)


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


async def _community(session: AsyncSession) -> uuid.UUID:
    c = Community(name=f"bday-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    return c.id


async def _user(
    session: AsyncSession,
    cid: uuid.UUID,
    name: str,
    birthday: date | None = TODAY_BDAY,
    *,
    show_to: str | None = "community",
    **kw: object,
) -> User:
    u = User(
        community_id=cid,
        email=f"{name}_{uuid.uuid4().hex[:6]}@nexara.dev",
        username=f"{name}_{uuid.uuid4().hex[:6]}",
        display_name=name,
        birthday=birthday,
        **kw,
    )
    session.add(u)
    await session.flush()
    if show_to is not None:
        session.add(UserSettings(user_id=u.id, community_id=cid, show_birthday_to=show_to))
        await session.flush()
    return u


@pytest.fixture
async def seeded(session: AsyncSession):
    """@brief Two communities with a mix of birthday/non-birthday users."""
    c1, c2, c3 = [await _community(session) for _ in range(3)]
    d = {"c1": c1, "c2": c2, "c3": c3}
    d["a"] = await _user(session, c1, "a", show_to="admin_only")
    d["admin"] = await _user(session, c1, "admin", OTHER_BDAY, role="admin")
    d["nosettings"] = await _user(session, c1, "nosettings", show_to=None)
    d["notoday"] = await _user(session, c1, "notoday", OTHER_BDAY)
    d["inactive"] = await _user(session, c1, "inactive", is_active=False)
    d["bot"] = await _user(session, c1, "bot", OTHER_BDAY, is_bot=True)
    d["b"] = await _user(session, c2, "b")
    # c3 only has a non-matching birthday and an inactive match.
    await _user(session, c3, "c3other", OTHER_BDAY)
    await _user(session, c3, "c3inactive", is_active=False)
    return d


async def test_community_ids_across_communities(session, seeded):
    ids = await BirthdayRepository(session).list_community_ids_with_birthday(MONTH, DAY)
    assert {seeded["c1"], seeded["c2"]} <= set(ids)
    assert seeded["c3"] not in ids
    assert len(ids) == len(set(ids))


async def test_birthday_users_filters_and_defaults(session, seeded):
    rows = await BirthdayRepository(session).list_birthday_users(seeded["c1"], MONTH, DAY)
    by_id = {u.id: s for u, s in rows}
    assert by_id == {seeded["a"].id: "admin_only", seeded["nosettings"].id: "community"}


async def test_birthday_users_scoped_to_community(session, seeded):
    rows = await BirthdayRepository(session).list_birthday_users(seeded["c2"], MONTH, DAY)
    assert [u.id for u, _ in rows] == [seeded["b"].id]


async def test_member_ids_exclude_inactive_and_bots(session, seeded):
    ids = set(await BirthdayRepository(session).list_member_ids(seeded["c1"]))
    assert ids == {
        seeded["a"].id,
        seeded["admin"].id,
        seeded["nosettings"].id,
        seeded["notoday"].id,
    }


async def test_admin_ids(session, seeded):
    ids = await BirthdayRepository(session).list_admin_ids(seeded["c1"])
    assert ids == [seeded["admin"].id]
    assert await BirthdayRepository(session).list_admin_ids(seeded["c2"]) == []
