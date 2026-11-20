"""
@file test_media_upload_aggregate.py
@brief Real-Postgres tests: home media aggregation includes unattached uploads.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.media import Media
from app.models.post import Post, PostMedia
from app.models.user import User
from app.repositories.subgroup_media_repo import SubgroupMediaRepository

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
    u = User(community_id=CID, email=f"mu_{tag}@nexara.dev", username=f"mu_{tag}", display_name="m")
    session.add(u)
    await session.flush()
    return u


async def _media(session: AsyncSession, user: User, age_min: int = 0) -> Media:
    m = Media(
        community_id=CID,
        uploader_id=user.id,
        filename="a.jpg",
        content_type="image/jpeg",
        storage_key=f"k/{uuid.uuid4()}",
        size_bytes=10,
        status="ready",
        created_at=datetime.now(UTC) - timedelta(minutes=age_min),
    )
    session.add(m)
    await session.flush()
    return m


async def _list(session, viewer, **kw):
    return await SubgroupMediaRepository(session).list_aggregated(
        community_id=CID, viewer_id=viewer.id, subgroup_ids=[], **kw
    )


@pytest.mark.parametrize("scope", ["all", "personal"])
async def test_own_orphan_upload_listed(session: AsyncSession, scope: str) -> None:
    me, other = await _user(session), await _user(session)
    mine = await _media(session, me)
    await _media(session, other)
    items, _ = await _list(session, me, scope=scope)
    assert [i["media_id"] for i in items] == [str(mine.id)]
    assert items[0]["source"] == "upload"
    assert items[0]["source_id"] is None
    assert items[0]["source_title"] is None


async def test_attached_upload_not_duplicated(session: AsyncSession) -> None:
    me = await _user(session)
    m = await _media(session, me)
    post = Post(community_id=CID, author_id=me.id, content="hi", visibility="community")
    session.add(post)
    await session.flush()
    session.add(PostMedia(post_id=post.id, media_id=m.id))
    await session.flush()
    items, _ = await _list(session, me, scope="all")
    assert [i["source"] for i in items] == ["post"]


async def test_upload_newest_first_and_cursor(session: AsyncSession) -> None:
    me = await _user(session)
    old = await _media(session, me, age_min=10)
    new = await _media(session, me, age_min=1)
    page1, cur = await _list(session, me, limit=1)
    assert [i["media_id"] for i in page1] == [str(new.id)] and cur
    page2, _ = await _list(session, me, limit=1, cursor=cur)
    assert [i["media_id"] for i in page2] == [str(old.id)]


async def test_source_filter_upload_and_post(session: AsyncSession) -> None:
    me = await _user(session)
    await _media(session, me)
    only_post, _ = await _list(session, me, source="post")
    only_up, _ = await _list(session, me, source="upload")
    assert only_post == [] and len(only_up) == 1
