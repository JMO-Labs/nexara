"""
@file test_home_needs_repo.py
@brief Real-Postgres integration tests for HomeNeedsRepository.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.event import Event, EventAttendance
from app.models.list import List, ListItem
from app.models.poll import Poll, PollOption, PollVote
from app.models.post import Post
from app.models.prompt import Prompt, PromptPost
from app.models.user import User
from app.repositories.home_needs_repo import HomeNeedsRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


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


async def _user(session: AsyncSession, cid: uuid.UUID) -> User:
    tag = uuid.uuid4().hex[:8]
    u = User(community_id=cid, email=f"n_{tag}@nexara.dev", username=f"n_{tag}", display_name="n")
    session.add(u)
    await session.flush()
    return u


@pytest.fixture
async def world(session: AsyncSession):
    c = Community(name=f"needs-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    viewer = await _user(session, c.id)
    other = await _user(session, c.id)
    return c.id, viewer, other


async def _event(session, cid, author, days=2.0, **kw) -> Event:
    start = NOW + timedelta(days=days)
    ev = Event(
        community_id=cid,
        author_id=author.id,
        title=kw.pop("title", "E"),
        starts_at=start,
        ends_at=start + timedelta(hours=1),
        ical_uid=f"{uuid.uuid4()}@t",
        **kw,
    )
    session.add(ev)
    await session.flush()
    return ev


async def _post(session, cid, author, created=NOW - timedelta(days=1), **kw) -> Post:
    p = Post(community_id=cid, author_id=author.id, content="x", created_at=created, **kw)
    session.add(p)
    await session.flush()
    return p


async def _poll(session, cid, author, **kw) -> Poll:
    post = await _post(session, cid, author)
    poll = Poll(community_id=cid, post_id=post.id, created_by=author.id, question="Q?", **kw)
    session.add(poll)
    await session.flush()
    return poll


async def test_rsvps_basic_and_exclusions(session, world):
    cid, viewer, other = world
    repo = HomeNeedsRepository(session)
    ok = await _event(session, cid, other, 2, title="ok")
    rsvped = await _event(session, cid, other, 3)
    session.add(EventAttendance(community_id=cid, event_id=rsvped.id, user_id=viewer.id))
    await _event(session, cid, viewer, 4)  # own
    await _event(session, cid, other, 15)  # too far
    await _event(session, cid, other, 5, visibility="private")
    await session.flush()
    rows = await repo.pending_rsvps(viewer.id, cid, [], NOW)
    assert [e.id for e in rows] == [ok.id]


async def test_rsvps_subgroup_visibility(session, world):
    from app.models.subgroup import Subgroup

    cid, viewer, other = world
    sg = Subgroup(community_id=cid, name="g", slug=f"g-{uuid.uuid4().hex[:6]}")
    session.add(sg)
    await session.flush()
    ev = await _event(session, cid, other, 2, visibility="subgroup", subgroup_id=sg.id)
    repo = HomeNeedsRepository(session)
    assert await repo.pending_rsvps(viewer.id, cid, [], NOW) == []
    assert [e.id for e in await repo.pending_rsvps(viewer.id, cid, [sg.id], NOW)] == [ev.id]


async def test_polls_exclusions(session, world):
    cid, viewer, other = world
    repo = HomeNeedsRepository(session)
    ok = await _poll(session, cid, other)
    voted = await _poll(session, cid, other)
    opt = PollOption(poll_id=voted.id, label="a")
    session.add(opt)
    await session.flush()
    session.add(PollVote(poll_id=voted.id, option_id=opt.id, user_id=viewer.id))
    await _poll(session, cid, other, expires_at=NOW - timedelta(hours=1))
    await _poll(session, cid, other, closed=True)
    await _poll(session, cid, viewer)
    await session.flush()
    rows = await repo.open_polls(viewer.id, cid, [], NOW)
    assert [p.id for p in rows] == [ok.id]


async def _prompt(session, cid, author) -> PromptPost:
    pr = Prompt(community_id=cid, title="Gratitude", body="b", frequency_type="weekly")
    session.add(pr)
    post = await _post(session, cid, author, is_prompt_post=True)
    await session.flush()
    pp = PromptPost(
        community_id=cid,
        prompt_id=pr.id,
        post_id=post.id,
        fired_at=date(2026, 11, 18),
        expires_at=NOW + timedelta(days=1),
    )
    session.add(pp)
    await session.flush()
    return pp


async def test_prompt_unanswered_then_answered(session, world):
    cid, viewer, other = world
    repo = HomeNeedsRepository(session)
    pp = await _prompt(session, cid, other)
    res = await repo.unanswered_prompt(viewer.id, cid, NOW)
    assert res is not None and res[0] == pp.id and res[2] == "Gratitude"
    await _post(session, cid, viewer, reply_to_prompt_id=pp.id)
    assert await repo.unanswered_prompt(viewer.id, cid, NOW) is None


async def test_prompt_expired_excluded(session, world):
    cid, viewer, other = world
    pp = await _prompt(session, cid, other)
    pp.expires_at = NOW - timedelta(minutes=1)
    await session.flush()
    assert await HomeNeedsRepository(session).unanswered_prompt(viewer.id, cid, NOW) is None


async def _list(session, cid, owner, **kw) -> List:
    lst = List(community_id=cid, owner_id=owner.id, title=kw.pop("title", "L"), **kw)
    session.add(lst)
    await session.flush()
    return lst


async def test_list_items_due_and_completed(session, world):
    cid, viewer, other = world
    repo = HomeNeedsRepository(session)
    lst = await _list(session, cid, other, visibility="community", title="Chores")
    soon = NOW + timedelta(days=1)
    session.add(ListItem(list_id=lst.id, due_at=soon))
    session.add(ListItem(list_id=lst.id, due_at=soon + timedelta(days=1)))
    session.add(ListItem(list_id=lst.id, due_at=soon, completed=True))
    session.add(ListItem(list_id=lst.id, due_at=NOW + timedelta(days=9)))
    hidden = await _list(session, cid, other, visibility="private")
    session.add(ListItem(list_id=hidden.id, due_at=soon))
    await session.flush()
    count, list_id, title = await repo.due_list_items(viewer.id, cid, [], NOW)
    assert (count, list_id, title) == (2, lst.id, "Chores")


async def test_list_items_none(session, world):
    cid, viewer, _ = world
    res = await HomeNeedsRepository(session).due_list_items(viewer.id, cid, [], NOW)
    assert res == (0, None, None)
