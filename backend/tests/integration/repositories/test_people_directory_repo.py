"""
@file test_people_directory_repo.py
@brief Real-Postgres integration tests for PeopleDirectoryRepository.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.moderation import UserBlock
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.people_directory_repo import PeopleDirectoryRepository

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
    c = Community(name=f"pd-{uuid.uuid4().hex[:6]}")
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


async def _group(session, cid, name, members) -> Subgroup:
    g = Subgroup(community_id=cid, name=name, slug=f"{name}-{uuid.uuid4().hex[:6]}")
    session.add(g)
    await session.flush()
    for m in members:
        session.add(SubgroupMember(community_id=cid, subgroup_id=g.id, user_id=m.id))
    await session.flush()
    return g


async def test_excludes_viewer_bots_inactive_blocked_both_ways(session, community):
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
    rows = await PeopleDirectoryRepository(session).page(
        viewer.id,
        cid,
        viewer_is_admin=False,
        q=None,
        online_ids=None,
        groups_only=False,
        offset=0,
        limit=10,
    )
    assert {r.user.id for r in rows} == {ok.id}


async def _run(session, viewer, cid, **kw):
    args = {
        "viewer_is_admin": False,
        "q": None,
        "online_ids": None,
        "groups_only": False,
        "offset": 0,
        "limit": 10,
    }
    args.update(kw)
    return await PeopleDirectoryRepository(session).page(viewer.id, cid, **args)


async def test_search_matches_name_or_username_and_escapes_wildcards(session, community):
    cid = community.id
    viewer = await _user(session, cid, "viewer")
    ruth = await _user(session, cid, "Ruth")
    await _user(session, cid, "Leo")
    rows = await _run(session, viewer, cid, q="rut")
    assert [r.user.id for r in rows] == [ruth.id]
    assert await _run(session, viewer, cid, q="%") == []


async def test_profile_visibility_hides_admin_only_from_non_admins(session, community):
    cid = community.id
    viewer = await _user(session, cid, "viewer")
    hidden = await _user(session, cid, "hidden")
    session.add(UserSettings(user_id=hidden.id, community_id=cid, profile_visible_to="admin_only"))
    await session.flush()
    assert await _run(session, viewer, cid) == []
    rows = await _run(session, viewer, cid, viewer_is_admin=True)
    assert [r.user.id for r in rows] == [hidden.id]


async def test_online_filter_uses_ids_and_respects_show_online_status(session, community):
    cid = community.id
    viewer = await _user(session, cid, "viewer")
    on = await _user(session, cid, "on")
    shy = await _user(session, cid, "shy")
    off = await _user(session, cid, "off")
    session.add(UserSettings(user_id=shy.id, community_id=cid, show_online_status=False))
    await session.flush()
    ids = [str(on.id), str(shy.id)]
    rows = await _run(session, viewer, cid, online_ids=ids)
    assert {r.user.id for r in rows} == {on.id}
    assert off.id not in {r.user.id for r in rows}
    assert await _run(session, viewer, cid, online_ids=[]) == []


async def test_groups_filter_and_shared_groups_attached(session, community):
    cid = community.id
    viewer = await _user(session, cid, "viewer")
    mate = await _user(session, cid, "mate")
    await _user(session, cid, "stranger")
    g = await _group(session, cid, "Chess", [viewer, mate])
    rows = await _run(session, viewer, cid, groups_only=True)
    assert [r.user.id for r in rows] == [mate.id]
    assert [(x[0], x[1]) for x in rows[0].shared_groups] == [(g.id, "Chess")]
    everyone = await _run(session, viewer, cid)
    assert len(everyone) == 2


async def test_pagination_orders_by_name_with_offset(session, community):
    cid = community.id
    viewer = await _user(session, cid, "viewer")
    for n in ("Cy", "Al", "Bo"):
        await _user(session, cid, n)
    first = await _run(session, viewer, cid, limit=2)
    rest = await _run(session, viewer, cid, offset=2, limit=2)
    assert [r.user.display_name for r in first] == ["Al", "Bo"]
    assert [r.user.display_name for r in rest] == ["Cy"]
