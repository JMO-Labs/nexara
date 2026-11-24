"""
@file nsfw_fixtures.py
@brief Shared real-Postgres fixtures for the NSFW gating tests: users of each
       age group, NSFW/safe posts, media in posts and albums.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 - registers all mapped classes
from app.models.gallery import Gallery, GalleryItem
from app.models.media import Media
from app.models.post import Post, PostMedia
from app.models.user import User

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture(name="session")
async def nsfw_session() -> Any:
    """@brief Transactional session rolled back after each test."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


def years_ago(n: int) -> date:
    """@brief A birthday that makes the person ``n`` or ``n + 1`` today."""
    return date(datetime.now(UTC).year - n - 1, 6, 15)


async def make_user(
    s: AsyncSession, *, birthday: date | None = None, age_group: str | None = None
) -> User:
    """@brief Insert a user; no birthday and no group = unknown age."""
    tag = uuid.uuid4().hex[:10]
    u = User(
        community_id=CID,
        email=f"nsfw_{tag}@nexara.dev",
        username=f"nsfw_{tag}",
        display_name=f"N {tag}",
        birthday=birthday,
        age_group=age_group,
    )
    s.add(u)
    await s.flush()
    return u


async def adult(s: AsyncSession) -> User:
    """@brief Adult by birthday."""
    return await make_user(s, birthday=years_ago(30))


async def teen(s: AsyncSession) -> User:
    """@brief Teen by birthday."""
    return await make_user(s, birthday=years_ago(15))


async def make_post(
    s: AsyncSession, author: User, *, nsfw: bool, content: str = "hello", **kw: Any
) -> Post:
    """@brief Insert a community post (NSFW or not)."""
    p = Post(
        community_id=CID,
        author_id=author.id,
        content=content,
        visibility=kw.pop("visibility", "community"),
        is_nsfw=nsfw,
        **kw,
    )
    s.add(p)
    await s.flush()
    await s.refresh(p)
    return p


async def make_media(s: AsyncSession, owner: User, *, nsfw: bool = False) -> Media:
    """@brief Insert a ready image."""
    m = Media(
        community_id=CID,
        uploader_id=owner.id,
        filename="a.jpg",
        content_type="image/jpeg",
        storage_key=f"k/{uuid.uuid4()}",
        thumbnail_key=f"t/{uuid.uuid4()}",
        size_bytes=10,
        status="ready",
        is_nsfw=nsfw,
    )
    s.add(m)
    await s.flush()
    return m


async def attach(s: AsyncSession, post: Post, media: Media) -> None:
    """@brief Attach media to a post."""
    s.add(PostMedia(post_id=post.id, media_id=media.id))
    await s.flush()


async def make_album(s: AsyncSession, owner: User, *, nsfw: bool, media: Media) -> Gallery:
    """@brief Community album holding ``media``."""
    g = Gallery(
        community_id=CID,
        owner_id=owner.id,
        title=f"album {uuid.uuid4().hex[:6]}",
        visibility="community",
        is_nsfw=nsfw,
    )
    s.add(g)
    await s.flush()
    s.add(GalleryItem(community_id=CID, gallery_id=g.id, media_id=media.id, added_by=owner.id))
    await s.flush()
    return g


def ids(items: list[dict[str, Any]]) -> set[str]:
    """@brief String ids of enriched post dicts."""
    return {str(i["id"]) for i in items}


def group_repos(s: AsyncSession) -> dict[str, Any]:
    """@brief Subgroup repos ``NsfwModerationService`` takes by injection."""
    from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository

    return {"groups": SubgroupRepository(s), "members": SubgroupMemberRepository(s)}
