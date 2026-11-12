"""
@file test_search_nsfw_repo.py
@brief Real-Postgres tests for NSFW filtering in search and ModerationRepository.set_nsfw.
"""

from __future__ import annotations

import os
import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.media import Media
from app.models.poll import Poll
from app.models.post import Comment, Post
from app.models.user import User
from app.repositories.moderation_repo import ModerationRepository
from app.repositories.search_repo import SearchRepository
from app.services.search_service import SearchService

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_CID = uuid.UUID("00000000-0000-0000-0000-0000000000ff")
ADULT = date(1980, 1, 1)
MINOR = date(date.today().year - 10, 1, 1)


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


async def _user(s: AsyncSession, birthday: date | None = None) -> User:
    """@brief Insert a minimal user."""
    sfx = uuid.uuid4().hex[:8]
    u = User(
        community_id=CID,
        email=f"nsfw_{sfx}@nexara.dev",
        username=f"nsfw_{sfx}",
        display_name=f"NSFW {sfx}",
        birthday=birthday,
    )
    s.add(u)
    await s.flush()
    return u


async def _post(s: AsyncSession, author: User, content: str, nsfw: bool) -> Post:
    """@brief Insert a community post."""
    p = Post(
        community_id=CID,
        author_id=author.id,
        content=content,
        visibility="community",
        is_nsfw=nsfw,
    )
    s.add(p)
    await s.flush()
    await s.refresh(p)
    return p


async def _seed(s: AsyncSession, word: str) -> tuple[Post, Post]:
    """@brief Seed one NSFW and one normal post, each with a comment and a poll."""
    author = await _user(s, ADULT)
    nsfw = await _post(s, author, f"{word} spicy", True)
    safe = await _post(s, author, f"{word} wholesome", False)
    for p in (nsfw, safe):
        s.add(Comment(community_id=CID, post_id=p.id, author_id=author.id, content=word))
        s.add(Poll(community_id=CID, post_id=p.id, created_by=author.id, question="q?"))
    await s.flush()
    return nsfw, safe


class TestSearchServiceNsfw:
    """@brief End-to-end search through the real repository."""

    async def test_minor_sees_only_normal_post(self, session: AsyncSession):
        word = f"zq{uuid.uuid4().hex[:6]}"
        _, safe = await _seed(session, word)
        minor = await _user(session, MINOR)
        resp = await SearchService(SearchRepository(session), CID).search(
            word, minor, ["posts"], None, 20
        )
        posts = resp.results["posts"]
        assert [i.id for i in posts.items] == [safe.id]
        assert posts.total == 1
        assert posts.items[0].is_nsfw is False

    async def test_adult_sees_both_with_flags(self, session: AsyncSession):
        word = f"zq{uuid.uuid4().hex[:6]}"
        nsfw, safe = await _seed(session, word)
        adult = await _user(session, ADULT)
        resp = await SearchService(SearchRepository(session), CID).search(
            word, adult, ["posts"], None, 20
        )
        posts = resp.results["posts"]
        assert {i.id: i.is_nsfw for i in posts.items} == {nsfw.id: True, safe.id: False}
        assert posts.total == 2


class TestCommentPollNsfw:
    """@brief Comments and polls on NSFW posts are hidden unless include_nsfw."""

    @pytest.mark.parametrize("include,expected", [(False, 1), (True, 2)])
    async def test_comments(self, session: AsyncSession, include: bool, expected: int):
        word = f"zq{uuid.uuid4().hex[:6]}"
        nsfw, safe = await _seed(session, word)
        viewer = await _user(session)
        items, _, total = await SearchRepository(session).search_comments(
            word, "", CID, viewer.id, None, 20, include_nsfw=include
        )
        post_ids = {c.post_id for c, _ in items}
        assert total == expected
        assert safe.id in post_ids
        assert (nsfw.id in post_ids) is include

    @pytest.mark.parametrize("include,expected", [(False, 1), (True, 2)])
    async def test_polls(self, session: AsyncSession, include: bool, expected: int):
        word = f"zq{uuid.uuid4().hex[:6]}"
        nsfw, safe = await _seed(session, word)
        viewer = await _user(session)
        items, _, total = await SearchRepository(session).search_polls(
            word, "", CID, viewer.id, None, 20, include_nsfw=include
        )
        post_ids = {post.id for _, post, _ in items}
        assert total == expected
        assert safe.id in post_ids
        assert (nsfw.id in post_ids) is include


class TestSetNsfw:
    """@brief ModerationRepository.set_nsfw scoping."""

    async def test_sets_post_flag(self, session: AsyncSession):
        author = await _user(session)
        post = await _post(session, author, "x", False)
        assert await ModerationRepository(session).set_nsfw("posts", post.id, CID) is True
        await session.refresh(post)
        assert post.is_nsfw is True

    async def test_sets_media_flag(self, session: AsyncSession):
        author = await _user(session)
        m = Media(
            community_id=CID,
            uploader_id=author.id,
            filename="a.png",
            content_type="image/png",
            storage_key=f"k/{uuid.uuid4().hex}",
            size_bytes=1,
        )
        session.add(m)
        await session.flush()
        assert await ModerationRepository(session).set_nsfw("media", m.id, CID) is True
        await session.refresh(m)
        assert m.is_nsfw is True

    async def test_other_community_not_found(self, session: AsyncSession):
        author = await _user(session)
        post = await _post(session, author, "x", False)
        assert await ModerationRepository(session).set_nsfw("posts", post.id, OTHER_CID) is False

    async def test_deleted_post_not_found(self, session: AsyncSession):
        from sqlalchemy import func

        author = await _user(session)
        post = await _post(session, author, "x", False)
        post.deleted_at = func.now()
        await session.flush()
        assert await ModerationRepository(session).set_nsfw("posts", post.id, CID) is False

    async def test_missing_not_found(self, session: AsyncSession):
        assert await ModerationRepository(session).set_nsfw("posts", uuid.uuid4(), CID) is False
