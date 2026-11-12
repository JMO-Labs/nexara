"""
@file test_sassybot_repo.py
@brief Real-Postgres tests: SassybotRepository queries.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.media import Media
from app.models.post import Comment, Post, PostMedia
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.sassybot_repo import SassybotRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


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


async def _user(session: AsyncSession) -> User:
    tag = uuid.uuid4().hex[:8]
    u = User(community_id=CID, email=f"sb_{tag}@nexara.dev", username=f"sb_{tag}", display_name="s")
    session.add(u)
    await session.flush()
    return u


async def _post(session: AsyncSession, author: User) -> Post:
    p = Post(community_id=CID, author_id=author.id, content="hello")
    session.add(p)
    await session.flush()
    return p


async def _media(session: AsyncSession, user: User, ctype: str) -> Media:
    m = Media(
        community_id=CID,
        uploader_id=user.id,
        filename="f",
        content_type=ctype,
        storage_key=f"k/{uuid.uuid4()}",
        size_bytes=1,
    )
    session.add(m)
    await session.flush()
    return m


async def test_session_property(session: AsyncSession) -> None:
    assert SassybotRepository(session).session is session


async def test_post_and_author_missing_settings_means_allowed(session: AsyncSession) -> None:
    u = await _user(session)
    p = await _post(session, u)
    post, author, allowed = await SassybotRepository(session).get_post_and_author(p.id, CID)
    assert post.id == p.id and author.id == u.id and allowed is True


async def test_post_and_author_reflects_opt_out_setting(session: AsyncSession) -> None:
    u = await _user(session)
    p = await _post(session, u)
    session.add(UserSettings(user_id=u.id, community_id=CID, allow_sassybot=False))
    await session.flush()
    found = await SassybotRepository(session).get_post_and_author(p.id, CID)
    assert found is not None and found[2] is False


async def test_post_and_author_none_when_missing(session: AsyncSession) -> None:
    assert await SassybotRepository(session).get_post_and_author(uuid.uuid4(), CID) is None


async def test_get_community(session: AsyncSession) -> None:
    repo = SassybotRepository(session)
    community = await repo.get_community(CID)
    assert community is not None and community.id == CID


async def test_community_id_for_post(session: AsyncSession) -> None:
    repo = SassybotRepository(session)
    p = await _post(session, await _user(session))
    assert await repo.get_community_id_for_post(p.id) == CID
    assert await repo.get_community_id_for_post(uuid.uuid4()) is None


async def test_get_images_filters_and_orders(session: AsyncSession) -> None:
    u = await _user(session)
    p = await _post(session, u)
    img2, vid, img1 = (
        await _media(session, u, "image/png"),
        await _media(session, u, "video/mp4"),
        await _media(session, u, "image/jpeg"),
    )
    for pos, m in ((1, img2), (2, vid), (0, img1)):
        session.add(PostMedia(post_id=p.id, media_id=m.id, position=pos))
    await session.flush()
    images = await SassybotRepository(session).get_images(p.id)
    assert [m.id for m in images] == [img1.id, img2.id]


async def test_count_bot_comments_ignores_others_and_deleted(session: AsyncSession) -> None:
    from datetime import UTC, datetime

    bot, other = await _user(session), await _user(session)
    p = await _post(session, other)
    for author, deleted in ((bot, False), (bot, False), (bot, True), (other, False)):
        session.add(
            Comment(
                community_id=CID,
                post_id=p.id,
                author_id=author.id,
                content="c",
                deleted_at=datetime.now(UTC) if deleted else None,
            )
        )
    await session.flush()
    assert await SassybotRepository(session).count_bot_comments(p.id, bot.id, CID) == 2
