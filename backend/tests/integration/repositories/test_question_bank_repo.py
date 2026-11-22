"""
@file test_question_bank_repo.py
@brief next_question ordering, status filtering and builtin recycling (real DB).
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.question_bank import QuestionBank
from app.repositories.question_bank_repo import QuestionBankRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)


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


async def _setup(session: AsyncSession) -> tuple[uuid.UUID, QuestionBankRepository]:
    c = Community(name=f"qb-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    return c.id, QuestionBankRepository(session)


async def _add(repo: QuestionBankRepository, cid: uuid.UUID, text: str, source: str, status: str):
    return await repo.create(
        QuestionBank(community_id=cid, text=text, source=source, status=status)
    )


async def test_prefers_admin_and_member_over_builtin(session: AsyncSession) -> None:
    cid, repo = await _setup(session)
    await _add(repo, cid, "b1", "builtin", "approved")
    await _add(repo, cid, "pending", "member", "pending")
    await _add(repo, cid, "rejected", "member", "rejected")
    admin = await _add(repo, cid, "admin q", "admin", "approved")
    got = await repo.next_question(cid)
    assert got is not None and got.id == admin.id


async def test_skips_pending_and_rejected(session: AsyncSession) -> None:
    cid, repo = await _setup(session)
    await _add(repo, cid, "pending", "member", "pending")
    await _add(repo, cid, "rejected", "admin", "rejected")
    assert await repo.next_question(cid) is None


async def test_exhausted_builtin_recycles(session: AsyncSession) -> None:
    cid, repo = await _setup(session)
    row = await _add(repo, cid, "b1", "builtin", "approved")
    first = await repo.next_question(cid)
    assert first is not None
    await repo.mark_used(first, None)
    again = await repo.next_question(cid)
    assert again is not None and again.id == row.id and again.used_at is None


async def test_admin_question_is_not_recycled(session: AsyncSession) -> None:
    cid, repo = await _setup(session)
    admin = await _add(repo, cid, "admin q", "admin", "approved")
    await repo.mark_used(admin, None)
    assert await repo.next_question(cid) is None
