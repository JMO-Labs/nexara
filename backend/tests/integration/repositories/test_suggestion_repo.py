"""
@file test_suggestion_repo.py
@brief Real-Postgres integration tests for SuggestionRepository.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.core.exceptions import ConflictError, NotFoundError
from app.models.community import Community
from app.models.event import Event
from app.models.user import User
from app.repositories.suggestion_repo import SuggestionRepository

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


async def _community(session: AsyncSession) -> uuid.UUID:
    c = Community(name=f"sugg-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    return c.id


async def _user(session: AsyncSession, cid: uuid.UUID) -> User:
    tag = uuid.uuid4().hex[:8]
    u = User(community_id=cid, email=f"s_{tag}@nexara.dev", username=f"s_{tag}", display_name=tag)
    session.add(u)
    await session.flush()
    return u


async def _event(
    session: AsyncSession, cid: uuid.UUID, author: uuid.UUID, title: str, **kw: object
) -> None:
    start = datetime.now(UTC) + timedelta(days=1)
    session.add(
        Event(
            community_id=cid,
            author_id=author,
            title=title,
            starts_at=start,
            ends_at=start + timedelta(hours=1),
            ical_uid=f"{uuid.uuid4()}@nexara.test",
            **kw,
        )
    )
    await session.flush()


async def test_create_and_list_pending_filters_type(session):
    cid = await _community(session)
    repo = SuggestionRepository(session)
    p = await repo.create(cid, "prompt", {"text": "hi"})
    poll = await repo.create(cid, "poll", {"question": "Q", "options": ["a", "b", "c", "d"]})
    assert p.id and p.suggested_by == "ai" and p.approved_at is None
    assert {s.id for s in await repo.list_pending(cid)} == {p.id, poll.id}
    assert [s.id for s in await repo.list_pending(cid, "prompt")] == [p.id]
    assert [s.id for s in await repo.list_pending(cid, "poll")] == [poll.id]


async def test_list_pending_excludes_reviewed_and_other_communities(session):
    cid, other = await _community(session), await _community(session)
    admin = await _user(session, cid)
    repo = SuggestionRepository(session)
    keep = await repo.create(cid, "prompt", {"text": "keep"})
    approved = await repo.create(cid, "prompt", {"text": "a"})
    rejected = await repo.create(cid, "prompt", {"text": "r"})
    await repo.create(other, "prompt", {"text": "other"})
    await repo.approve(approved.id, admin.id, cid)
    await repo.reject(rejected.id, cid)
    assert [s.id for s in await repo.list_pending(cid)] == [keep.id]


async def test_approve_sets_fields_and_second_review_conflicts(session):
    cid = await _community(session)
    admin = await _user(session, cid)
    repo = SuggestionRepository(session)
    s = await repo.create(cid, "prompt", {"text": "x"})
    done = await repo.approve(s.id, admin.id, cid)
    assert done.approved_at is not None and done.approved_by == admin.id
    with pytest.raises(ConflictError):
        await repo.approve(s.id, admin.id, cid)
    with pytest.raises(ConflictError):
        await repo.reject(s.id, cid)


async def test_reject_sets_rejected_at(session):
    cid = await _community(session)
    repo = SuggestionRepository(session)
    s = await repo.create(cid, "poll", {"question": "Q"})
    assert (await repo.reject(s.id, cid)).rejected_at is not None


async def test_review_unknown_or_foreign_id_not_found(session):
    cid, other = await _community(session), await _community(session)
    admin = await _user(session, cid)
    repo = SuggestionRepository(session)
    foreign = await repo.create(other, "prompt", {"text": "x"})
    with pytest.raises(NotFoundError):
        await repo.approve(uuid.uuid4(), admin.id, cid)
    with pytest.raises(NotFoundError):
        await repo.reject(foreign.id, cid)


async def test_upcoming_event_titles_only_community_visible(session):
    cid = await _community(session)
    author = await _user(session, cid)
    await _event(session, cid, author.id, "Picnic")
    await _event(session, cid, author.id, "Secret", visibility="private")
    await _event(session, cid, author.id, "Club only", visibility="subgroup")
    await _event(session, cid, author.id, "Gone", source_removed=True)
    titles = await SuggestionRepository(session).upcoming_event_titles(cid, 10)
    assert titles == ["Picnic"]
