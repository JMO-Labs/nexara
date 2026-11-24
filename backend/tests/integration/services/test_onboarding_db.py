"""
@file test_onboarding_db.py
@brief Real-Postgres checks: has_relation, required-step data checks, backfill.
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.config import get_settings
from app.models.relation import Relation
from app.models.user import User
from app.repositories.onboarding_repo import OnboardingRepository
from app.services.onboarding_service import OnboardingService

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)


@pytest.fixture
async def session():
    """@brief Session inside a transaction rolled back after the test."""
    engine = create_async_engine(DB_URL)
    async with engine.connect() as conn:
        trans = await conn.begin()
        async with async_sessionmaker(
            bind=conn, class_=AsyncSession, expire_on_commit=False
        )() as s:
            yield s
        await trans.rollback()
    await engine.dispose()


async def _user(s: AsyncSession, cid: uuid.UUID, **kw) -> User:
    tag = uuid.uuid4().hex[:10]
    u = User(
        community_id=cid,
        email=f"ob_{tag}@nexara.dev",
        username=f"ob_{tag}",
        display_name="Ob",
        **kw,
    )
    s.add(u)
    await s.flush()
    return u


async def test_missing_and_complete_against_real_rows(session):
    cid = uuid.UUID(get_settings().COMMUNITY_ID)
    await session.execute(
        text("UPDATE communities SET onboarding_required = :r WHERE id = :i").bindparams(
            r=["birthday", "contact", "family"], i=cid
        )
    )
    me = await _user(session, cid)
    other = await _user(session, cid)
    repo = OnboardingRepository(session)
    svc = OnboardingService(repo, cid, session, me)

    assert await repo.has_relation(cid, me.id) is False
    required = await svc._required()
    assert await svc._missing(required) == ["birthday", "contact", "family"]

    me.birthday = date(1990, 1, 1)
    me.phone = "555"
    session.add(
        Relation(
            community_id=cid,
            from_user_id=me.id,
            to_user_id=other.id,
            kind="friend",
            created_by=me.id,
        )
    )
    await session.flush()
    assert await repo.has_relation(cid, me.id) is True
    assert await repo.has_relation(cid, other.id) is True
    assert await svc._missing(required) == []

    state = await svc.complete()
    assert state.done is True and state.step == 6


async def test_backfill_marks_existing_users_done(session):
    """@brief The migration's backfill statement stamps pending users; new rows start pending."""
    src = (Path(__file__).parents[3] / "alembic/versions/0074_onboarding_age.py").read_text()
    m = re.search(r'op\.execute\("(UPDATE users SET onboarding_done_at[^"]*)"\)', src)
    assert m, "backfill statement missing from migration 0074"
    new = await _user(session, uuid.UUID(get_settings().COMMUNITY_ID))
    assert new.onboarding_done_at is None
    await session.execute(text(m.group(1)))
    await session.refresh(new)
    assert new.onboarding_done_at is not None
    pending = await session.scalar(select(func.count()).where(User.onboarding_done_at.is_(None)))
    assert pending == 0
