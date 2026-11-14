"""
@file test_gallery_repo_block.py
@brief Real-Postgres tests: GalleryRepository.list_items block filter.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.gallery import Gallery, GalleryItem
from app.models.media import Media
from app.models.moderation import UserBlock
from app.models.user import User
from app.repositories.gallery_repo import GalleryRepository

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


async def _user(session: AsyncSession, name: str) -> User:
    u = User(
        community_id=COMMUNITY_ID,
        email=f"gb_{name}_{uuid.uuid4().hex[:6]}@nexara.dev",
        username=f"gb_{name}_{uuid.uuid4().hex[:6]}",
        display_name=name,
    )
    session.add(u)
    await session.flush()
    return u


async def _item(session: AsyncSession, gallery: Gallery, adder: User) -> GalleryItem:
    media = Media(
        community_id=COMMUNITY_ID,
        uploader_id=adder.id,
        filename="a.png",
        content_type="image/png",
        storage_key=f"k/{uuid.uuid4()}",
        size_bytes=1,
    )
    session.add(media)
    await session.flush()
    item = GalleryItem(
        community_id=COMMUNITY_ID,
        gallery_id=gallery.id,
        media_id=media.id,
        added_by=adder.id,
    )
    session.add(item)
    await session.flush()
    return item


async def _setup(session: AsyncSession):
    viewer, other, friend = [await _user(session, n) for n in "vof"]
    gallery = Gallery(community_id=COMMUNITY_ID, owner_id=friend.id, title="g")
    session.add(gallery)
    await session.flush()
    bad = await _item(session, gallery, other)
    good = await _item(session, gallery, friend)
    return viewer, other, gallery, bad, good


async def test_item_by_blocked_user_hidden(session: AsyncSession) -> None:
    viewer, other, gallery, _bad, good = await _setup(session)
    session.add(UserBlock(blocker_id=viewer.id, blocked_id=other.id, community_id=COMMUNITY_ID))
    await session.flush()

    rows, _ = await GalleryRepository(session).list_items(gallery.id, viewer_id=viewer.id)

    assert [r.id for r in rows] == [good.id]


async def test_item_by_blocking_user_hidden(session: AsyncSession) -> None:
    viewer, other, gallery, _bad, good = await _setup(session)
    session.add(UserBlock(blocker_id=other.id, blocked_id=viewer.id, community_id=COMMUNITY_ID))
    await session.flush()

    rows, _ = await GalleryRepository(session).list_items(gallery.id, viewer_id=viewer.id)

    assert [r.id for r in rows] == [good.id]


async def test_no_viewer_returns_all(session: AsyncSession) -> None:
    _v, _o, gallery, _bad, _good = await _setup(session)
    rows, _ = await GalleryRepository(session).list_items(gallery.id)
    assert len(rows) == 2
