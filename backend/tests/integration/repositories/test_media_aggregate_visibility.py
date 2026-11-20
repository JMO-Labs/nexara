"""
@file test_media_aggregate_visibility.py
@brief Real-Postgres: home media aggregation honours post/gallery/event
       visibility (private = author/owner only) and pages correctly across
       sources when each source is limited before the merge.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.gallery import Gallery, GalleryItem
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
    u = User(community_id=CID, email=f"mv_{tag}@nexara.dev", username=f"mv_{tag}", display_name="v")
    session.add(u)
    await session.flush()
    return u


async def _media(session: AsyncSession, owner: User, age_min: int = 0) -> Media:
    m = Media(
        community_id=CID,
        uploader_id=owner.id,
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


async def _post_with_media(session: AsyncSession, author: User, visibility: str) -> Media:
    m = await _media(session, author)
    p = Post(community_id=CID, author_id=author.id, content="p", visibility=visibility)
    session.add(p)
    await session.flush()
    session.add(PostMedia(post_id=p.id, media_id=m.id))
    await session.flush()
    return m


async def _gallery_with_media(
    session: AsyncSession, owner: User, visibility: str, age_min: int = 0
) -> Media:
    m = await _media(session, owner, age_min)
    g = Gallery(community_id=CID, owner_id=owner.id, title="g", visibility=visibility)
    session.add(g)
    await session.flush()
    session.add(
        GalleryItem(
            community_id=CID,
            gallery_id=g.id,
            media_id=m.id,
            added_by=owner.id,
            created_at=datetime.now(UTC) - timedelta(minutes=age_min),
        )
    )
    await session.flush()
    return m


async def _ids(session: AsyncSession, viewer: User, **kw) -> list[str]:
    items, _ = await SubgroupMediaRepository(session).list_aggregated(
        community_id=CID, viewer_id=viewer.id, subgroup_ids=[], **kw
    )
    return [i["media_id"] for i in items]


async def test_private_post_media_only_for_author(session: AsyncSession) -> None:
    author, other = await _user(session), await _user(session)
    m = await _post_with_media(session, author, "private")
    assert str(m.id) in await _ids(session, author, limit=200)
    assert str(m.id) not in await _ids(session, other, limit=200)


async def test_private_gallery_media_only_for_owner(session: AsyncSession) -> None:
    owner, other = await _user(session), await _user(session)
    m = await _gallery_with_media(session, owner, "private")
    assert str(m.id) in await _ids(session, owner, limit=200)
    assert str(m.id) not in await _ids(session, other, limit=200)


async def test_community_media_visible_to_all(session: AsyncSession) -> None:
    owner, other = await _user(session), await _user(session)
    m = await _gallery_with_media(session, owner, "community")
    assert str(m.id) in await _ids(session, other, limit=200)


async def test_paging_across_sources_is_newest_first_without_gaps(
    session: AsyncSession,
) -> None:
    me = await _user(session)
    expected = []
    for age in (1, 2, 3, 4, 5, 6):
        if age % 2:
            expected.append(await _gallery_with_media(session, me, "community", age))
        else:
            expected.append(await _media(session, me, age))  # orphan upload
    repo = SubgroupMediaRepository(session)
    seen: list[str] = []
    cursor = None
    for _ in range(10):
        items, cursor = await repo.list_aggregated(
            community_id=CID, viewer_id=me.id, subgroup_ids=[], limit=2, cursor=cursor
        )
        seen += [i["media_id"] for i in items]
        if not cursor:
            break
    mine = [str(m.id) for m in expected]
    assert [s for s in seen if s in mine] == mine
