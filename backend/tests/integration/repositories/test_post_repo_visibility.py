"""
@file test_post_repo_visibility.py
@brief Real-Postgres integration tests for PostRepository.list_feed visibility predicate.

Tests the security boundary: community posts, subgroup posts, and private posts
are returned only to the appropriate viewer.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.post import Post
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.post_repo import PostRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


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


async def _make_user(session: AsyncSession, suffix: str) -> User:
    """@brief Insert a minimal user and return it."""
    user = User(
        community_id=COMMUNITY_ID,
        email=f"vis_test_{suffix}@nexara.dev",
        username=f"vis_{suffix}",
        display_name=f"Vis {suffix}",
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def _make_subgroup(session: AsyncSession, slug: str) -> Subgroup:
    """@brief Insert a minimal subgroup and return it."""
    sg = Subgroup(
        community_id=COMMUNITY_ID,
        name=slug.capitalize(),
        slug=f"vis-{slug}-{uuid.uuid4().hex[:6]}",
    )
    session.add(sg)
    await session.flush()
    await session.refresh(sg)
    return sg


async def _join_subgroup(session: AsyncSession, user: User, sg: Subgroup) -> None:
    """@brief Add user as a member of subgroup."""
    membership = SubgroupMember(
        community_id=COMMUNITY_ID,
        subgroup_id=sg.id,
        user_id=user.id,
        role="member",
    )
    session.add(membership)
    await session.flush()


async def _make_post(
    session: AsyncSession,
    author: User,
    visibility: str,
    subgroup_id: uuid.UUID | None = None,
    content: str = "test content",
) -> Post:
    """@brief Insert a post and return it."""
    post = Post(
        community_id=COMMUNITY_ID,
        author_id=author.id,
        content=content,
        visibility=visibility,
        subgroup_id=subgroup_id,
    )
    session.add(post)
    await session.flush()
    await session.refresh(post)
    return post


class TestListFeedVisibilityIntegration:
    """@brief Integration tests for PostRepository.list_feed visibility predicate."""

    @pytest.mark.asyncio
    async def test_user_in_s1_sees_community_s1_and_own_private(self, session: AsyncSession):
        """
        User A in subgroups [S1]:
        list_feed returns: community post, S1 post, A's private post.
        Excludes: S2 post, B's private post.
        """
        user_a = await _make_user(session, f"a_{uuid.uuid4().hex[:6]}")
        user_b = await _make_user(session, f"b_{uuid.uuid4().hex[:6]}")
        sg1 = await _make_subgroup(session, "s1")
        sg2 = await _make_subgroup(session, "s2")
        await _join_subgroup(session, user_a, sg1)

        community_post = await _make_post(session, user_a, "community", content="community")
        sg1_post = await _make_post(session, user_a, "subgroup", sg1.id, content="s1post")
        sg2_post = await _make_post(session, user_b, "subgroup", sg2.id, content="s2post")
        a_private = await _make_post(session, user_a, "private", content="a_private")
        b_private = await _make_post(session, user_b, "private", content="b_private")

        repo = PostRepository(session)
        items, _ = await repo.list_feed(
            COMMUNITY_ID,
            viewer_id=user_a.id,
            subgroup_ids=[sg1.id],
            limit=50,
        )

        returned_ids = {item["id"] for item in items}

        assert str(community_post.id) in returned_ids, "community post should be visible"
        assert str(sg1_post.id) in returned_ids, "S1 post should be visible"
        assert str(a_private.id) in returned_ids, "A's private post should be visible"
        assert str(sg2_post.id) not in returned_ids, "S2 post should be excluded"
        assert str(b_private.id) not in returned_ids, "B's private post should be excluded"

    @pytest.mark.asyncio
    async def test_user_in_no_subgroups_sees_only_community_and_own_private(
        self, session: AsyncSession
    ):
        """
        User A in []:
        list_feed returns: community post, A's private post.
        Excludes: both subgroup posts, B's private post.
        """
        user_a = await _make_user(session, f"c_{uuid.uuid4().hex[:6]}")
        user_b = await _make_user(session, f"d_{uuid.uuid4().hex[:6]}")
        sg1 = await _make_subgroup(session, "t1")
        sg2 = await _make_subgroup(session, "t2")

        community_post = await _make_post(session, user_a, "community", content="community2")
        sg1_post = await _make_post(session, user_b, "subgroup", sg1.id, content="t1post")
        sg2_post = await _make_post(session, user_b, "subgroup", sg2.id, content="t2post")
        a_private = await _make_post(session, user_a, "private", content="a_priv2")
        b_private = await _make_post(session, user_b, "private", content="b_priv2")

        repo = PostRepository(session)
        items, _ = await repo.list_feed(
            COMMUNITY_ID,
            viewer_id=user_a.id,
            subgroup_ids=[],
            limit=50,
        )

        returned_ids = {item["id"] for item in items}

        assert str(community_post.id) in returned_ids, "community post should be visible"
        assert str(a_private.id) in returned_ids, "A's private post should be visible"
        assert str(sg1_post.id) not in returned_ids, "S1 post should be excluded"
        assert str(sg2_post.id) not in returned_ids, "S2 post should be excluded"
        assert str(b_private.id) not in returned_ids, "B's private post should be excluded"
