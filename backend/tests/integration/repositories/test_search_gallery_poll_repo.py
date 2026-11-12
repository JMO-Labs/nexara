"""
@file test_search_gallery_poll_repo.py
@brief Real-Postgres tests for gallery/poll search visibility, filters, paging.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.gallery import Gallery
from app.models.moderation import UserBlock
from app.models.poll import Poll
from app.models.post import Post
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.search_repo import SearchRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)
COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-0000000000ff")


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


async def _user(s: AsyncSession) -> User:
    """@brief Insert a minimal user."""
    sfx = uuid.uuid4().hex[:8]
    u = User(
        community_id=COMMUNITY_ID,
        email=f"gp_{sfx}@nexara.dev",
        username=f"gp_{sfx}",
        display_name=f"GP {sfx}",
    )
    s.add(u)
    await s.flush()
    return u


async def _subgroup(s: AsyncSession) -> Subgroup:
    """@brief Insert a minimal subgroup."""
    sg = Subgroup(community_id=COMMUNITY_ID, name="SG", slug=f"gp-{uuid.uuid4().hex[:8]}")
    s.add(sg)
    await s.flush()
    return sg


async def _gallery(
    s: AsyncSession,
    owner: User,
    title: str,
    visibility: str = "community",
    subgroup_id: uuid.UUID | None = None,
    community_id: uuid.UUID = COMMUNITY_ID,
) -> Gallery:
    """@brief Insert a gallery."""
    g = Gallery(
        community_id=community_id,
        owner_id=owner.id,
        title=title,
        visibility=visibility,
        subgroup_id=subgroup_id,
    )
    s.add(g)
    await s.flush()
    await s.refresh(g)
    return g


async def _poll(s: AsyncSession, author: User, content: str) -> tuple[Poll, Post]:
    """@brief Insert a community post with an attached poll."""
    post = Post(
        community_id=COMMUNITY_ID, author_id=author.id, content=content, visibility="community"
    )
    s.add(post)
    await s.flush()
    poll = Poll(community_id=COMMUNITY_ID, post_id=post.id, created_by=author.id, question="q?")
    s.add(poll)
    await s.flush()
    await s.refresh(poll)
    return poll, post


async def _galleries(s: AsyncSession, viewer: User, q: str, **kw) -> set[uuid.UUID]:
    """@brief Search galleries and return result ids."""
    items, _, _ = await SearchRepository(s).search_galleries(
        q, "", kw.get("community_id", COMMUNITY_ID), viewer.id, None, 50
    )
    return {g.id for g, _ in items}


async def _polls(s: AsyncSession, viewer: User, q: str) -> set[uuid.UUID]:
    """@brief Search polls and return poll ids."""
    items, _, _ = await SearchRepository(s).search_polls(q, "", COMMUNITY_ID, viewer.id, None, 50)
    return {p.id for p, _, _ in items}


class TestGallerySearchVisibility:
    """@brief Visibility and tenancy rules for search_galleries."""

    async def test_community_visible_to_any_member(self, session: AsyncSession):
        owner, viewer = await _user(session), await _user(session)
        g = await _gallery(session, owner, "zorblat summer")
        assert g.id in await _galleries(session, viewer, "zorblat")

    async def test_matches_on_description_only(self, session: AsyncSession):
        owner, viewer = await _user(session), await _user(session)
        g = await _gallery(session, owner, "plain title")
        g.description = "contains blorptastic word"
        await session.flush()
        assert g.id in await _galleries(session, viewer, "blorptastic")

    async def test_private_only_for_owner(self, session: AsyncSession):
        owner, other = await _user(session), await _user(session)
        g = await _gallery(session, owner, "zorblat secret", "private")
        assert g.id in await _galleries(session, owner, "zorblat")
        assert g.id not in await _galleries(session, other, "zorblat")

    async def test_subgroup_only_for_members(self, session: AsyncSession):
        owner, member, outsider = await _user(session), await _user(session), await _user(session)
        sg = await _subgroup(session)
        session.add(
            SubgroupMember(
                community_id=COMMUNITY_ID, subgroup_id=sg.id, user_id=member.id, role="member"
            )
        )
        await session.flush()
        g = await _gallery(session, owner, "zorblat club", "subgroup", sg.id)
        assert g.id in await _galleries(session, member, "zorblat")
        assert g.id not in await _galleries(session, outsider, "zorblat")

    async def test_other_community_excluded(self, session: AsyncSession):
        owner, viewer = await _user(session), await _user(session)
        mine = await _gallery(session, owner, "zorblat mine")
        session.add(Community(id=OTHER_COMMUNITY_ID, name=f"other-{uuid.uuid4().hex[:6]}"))
        await session.flush()
        other = await _gallery(session, owner, "zorblat theirs", community_id=OTHER_COMMUNITY_ID)
        ids = await _galleries(session, viewer, "zorblat")
        assert mine.id in ids and other.id not in ids

    async def test_pagination(self, session: AsyncSession):
        owner, viewer = await _user(session), await _user(session)
        a = await _gallery(session, owner, "pagetoken one")
        b = await _gallery(session, owner, "pagetoken two")
        repo = SearchRepository(session)
        args = ("pagetoken", "", COMMUNITY_ID, viewer.id)
        p1, nxt, total = await repo.search_galleries(*args, None, 1)
        assert nxt == "1" and total == 2 and len(p1) == 1
        p2, nxt2, _ = await repo.search_galleries(*args, "1", 1)
        assert nxt2 is None and len(p2) == 1
        assert {p1[0][0].id, p2[0][0].id} == {a.id, b.id}


class TestPollSearch:
    """@brief Post-content matching, soft-delete, and block rules for search_polls."""

    async def test_returned_on_post_content_match(self, session: AsyncSession):
        author, viewer = await _user(session), await _user(session)
        poll, _ = await _poll(session, author, "quixotic picnic vote")
        assert poll.id in await _polls(session, viewer, "quixotic")

    async def test_soft_deleted_post_excluded(self, session: AsyncSession):
        from datetime import UTC, datetime

        author, viewer = await _user(session), await _user(session)
        poll, post = await _poll(session, author, "quixotic deleted vote")
        post.deleted_at = datetime.now(UTC)
        await session.flush()
        assert poll.id not in await _polls(session, viewer, "quixotic")

    async def test_soft_deleted_poll_excluded(self, session: AsyncSession):
        from datetime import UTC, datetime

        author, viewer = await _user(session), await _user(session)
        poll, _ = await _poll(session, author, "quixotic polldel vote")
        poll.deleted_at = datetime.now(UTC)
        await session.flush()
        assert poll.id not in await _polls(session, viewer, "quixotic")

    @pytest.mark.parametrize("viewer_blocks", [True, False])
    async def test_blocked_either_direction_excluded(
        self, session: AsyncSession, viewer_blocks: bool
    ):
        author, viewer = await _user(session), await _user(session)
        poll, _ = await _poll(session, author, "quixotic blocked vote")
        blocker, blocked = (viewer, author) if viewer_blocks else (author, viewer)
        session.add(
            UserBlock(blocker_id=blocker.id, blocked_id=blocked.id, community_id=COMMUNITY_ID)
        )
        await session.flush()
        assert poll.id not in await _polls(session, viewer, "quixotic")

    async def test_pagination(self, session: AsyncSession):
        author, viewer = await _user(session), await _user(session)
        a, _ = await _poll(session, author, "pagepoll alpha")
        b, _ = await _poll(session, author, "pagepoll beta")
        repo = SearchRepository(session)
        p1, nxt, total = await repo.search_polls("pagepoll", "", COMMUNITY_ID, viewer.id, None, 1)
        assert nxt == "1" and total == 2 and len(p1) == 1
        p2, nxt2, _ = await repo.search_polls("pagepoll", "", COMMUNITY_ID, viewer.id, "1", 1)
        assert nxt2 is None and len(p2) == 1
        assert {p1[0][0].id, p2[0][0].id} == {a.id, b.id}
