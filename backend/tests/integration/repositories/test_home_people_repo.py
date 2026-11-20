"""
@file test_home_people_repo.py
@brief Real-Postgres integration tests for HomePeopleRepository.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.event import Event, EventAttendance
from app.models.moderation import UserBlock
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.home_people_repo import HomePeopleRepository

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


@pytest.fixture
async def community(session: AsyncSession) -> Community:
    c = Community(name=f"hp-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    return c


async def _user(session: AsyncSession, cid: uuid.UUID, name: str, **kw) -> User:
    tag = uuid.uuid4().hex[:6]
    u = User(
        community_id=cid,
        email=f"{name}_{tag}@nexara.dev",
        username=f"{name}_{tag}",
        display_name=name,
        **kw,
    )
    session.add(u)
    await session.flush()
    return u


async def _group(session, cid, creator, name, members) -> Subgroup:
    g = Subgroup(community_id=cid, name=name, slug=f"{name}-{uuid.uuid4().hex[:6]}")
    session.add(g)
    await session.flush()
    for m in members:
        session.add(SubgroupMember(community_id=cid, subgroup_id=g.id, user_id=m.id))
    await session.flush()
    return g


async def test_excludes_viewer_bots_inactive_and_blocked(session, community):
    cid = community.id
    viewer = await _user(session, cid, "viewer")
    ok = await _user(session, cid, "ok")
    await _user(session, cid, "bot", is_bot=True)
    await _user(session, cid, "inactive", is_active=False)
    blocked = await _user(session, cid, "blocked")
    blocker = await _user(session, cid, "blocker")
    session.add(UserBlock(community_id=cid, blocker_id=viewer.id, blocked_id=blocked.id))
    session.add(UserBlock(community_id=cid, blocker_id=blocker.id, blocked_id=viewer.id))
    await session.flush()

    rows = await HomePeopleRepository(session).candidates(viewer.id, cid, 10)
    ids = {r.user.id for r in rows}
    assert ids == {ok.id}


async def test_shared_groups_and_member_count(session, community):
    cid = community.id
    viewer = await _user(session, cid, "viewer")
    ana = await _user(session, cid, "ana")
    other = await _user(session, cid, "other")
    g = await _group(session, cid, viewer, "club", [viewer, ana, other])
    g.accent_color = "#112233"
    await _group(session, cid, viewer, "unshared", [other])
    await session.flush()

    rows = await HomePeopleRepository(session).candidates(viewer.id, cid, 10)
    by = {r.user.id: r for r in rows}
    assert by[ana.id].shared_groups == [(g.id, "club", "#112233", 3)]
    assert by[other.id].shared_groups == [(g.id, "club", "#112233", 3)]


async def test_shared_group_members_come_first_then_community_fill(session, community):
    cid = community.id
    viewer = await _user(session, cid, "viewer")
    mate = await _user(session, cid, "mate")
    stranger = await _user(session, cid, "stranger")
    await _group(session, cid, viewer, "club", [viewer, mate])

    rows = await HomePeopleRepository(session).candidates(viewer.id, cid, 10)
    assert [r.user.id for r in rows][0] == mate.id
    assert {r.user.id for r in rows} == {mate.id, stranger.id}
    stranger_row = next(r for r in rows if r.user.id == stranger.id)
    assert stranger_row.shared_groups == []


async def test_candidates_carry_privacy_flags_with_defaults(session, community):
    cid = community.id
    viewer = await _user(session, cid, "viewer")
    quiet = await _user(session, cid, "quiet")
    plain = await _user(session, cid, "plain")
    session.add(
        UserSettings(
            user_id=quiet.id,
            community_id=cid,
            show_online_status=False,
            show_last_seen=False,
            show_birthday_to="nobody",
        )
    )
    await session.flush()

    rows = await HomePeopleRepository(session).candidates(viewer.id, cid, 10)
    by = {r.user.id: r for r in rows}
    assert (by[quiet.id].show_online_status, by[quiet.id].show_last_seen) == (False, False)
    assert by[quiet.id].show_birthday_to == "nobody"
    assert (by[plain.id].show_online_status, by[plain.id].show_last_seen) == (True, True)
    assert by[plain.id].show_birthday_to == "community"


async def test_shared_event_counts_mutual_attending_only(session, community):
    cid = community.id
    viewer = await _user(session, cid, "viewer")
    ana = await _user(session, cid, "ana")
    now = datetime.now(UTC)

    def _event(delta: timedelta) -> Event:
        e = Event(
            community_id=cid,
            author_id=viewer.id,
            title="e",
            ical_uid=f"{uuid.uuid4()}@test",
            starts_at=now + delta,
            ends_at=now + delta + timedelta(hours=1),
        )
        session.add(e)
        return e

    mutual = _event(timedelta(days=-3))
    only_viewer = _event(timedelta(days=2))
    far = _event(timedelta(days=-60))
    await session.flush()
    for e, users, status in [
        (mutual, (viewer, ana), "attending"),
        (only_viewer, (viewer,), "attending"),
        (far, (viewer, ana), "attending"),
    ]:
        for u in users:
            session.add(
                EventAttendance(community_id=cid, event_id=e.id, user_id=u.id, status=status)
            )
    maybe = _event(timedelta(days=1))
    await session.flush()
    session.add(EventAttendance(community_id=cid, event_id=maybe.id, user_id=viewer.id))
    session.add(
        EventAttendance(community_id=cid, event_id=maybe.id, user_id=ana.id, status="maybe")
    )
    await session.flush()

    counts = await HomePeopleRepository(session).shared_event_counts(viewer.id, [ana.id], cid)
    assert counts == {ana.id: 1}


async def test_shared_event_counts_empty_ids(session, community):
    repo = HomePeopleRepository(session)
    assert await repo.shared_event_counts(uuid.uuid4(), [], community.id) == {}
