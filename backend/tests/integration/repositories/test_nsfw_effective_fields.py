"""
@file test_nsfw_effective_fields.py
@brief Real Postgres: photo/item responses carry the effective NSFW flag and
       lock (own or container source rows) plus the photo's own flag.
"""

from __future__ import annotations

from app.models.media_nsfw_source import MediaNsfwSource
from app.repositories.gallery_repo import GalleryRepository
from app.repositories.media_repo import MediaRepository
from app.schemas.gallery import GalleryItemBulkCreate
from app.services.gallery_service import GalleryService
from app.services.media.serving import effective_response
from tests.integration.repositories.nsfw_fixtures import (
    CID,
    adult,
    make_album,
    make_media,
    nsfw_session,  # noqa: F401 - provides the "session" fixture
)


async def _sourced(session, owner, level: str = "moderator"):
    m = await make_media(session, owner)
    alb = await make_album(session, owner, nsfw=False, media=m)
    session.add(
        MediaNsfwSource(
            media_id=m.id, source_kind="gallery", source_id=alb.id, community_id=CID, level=level
        )
    )
    await session.flush()
    return m, alb


class TestEffectiveFields:
    async def test_media_response_shows_source_lock(self, session) -> None:
        me = await adult(session)
        m, _alb = await _sourced(session, me, "admin")
        out = await effective_response(MediaRepository(session), m)
        assert out.is_nsfw and not out.is_nsfw_own
        assert out.nsfw_locked and out.nsfw_lock_level == "admin"

    async def test_media_response_own_flag_only(self, session) -> None:
        me = await adult(session)
        m = await make_media(session, me, nsfw=True)
        out = await effective_response(MediaRepository(session), m)
        assert out.is_nsfw and out.is_nsfw_own and not out.nsfw_locked

    async def test_item_list_shows_source_lock(self, session) -> None:
        me = await adult(session)
        m, alb = await _sourced(session, me)
        svc = GalleryService(GalleryRepository(session), CID, session)
        (it,) = await svc.list_items(alb.id, me.id)
        assert it.is_nsfw and not it.is_nsfw_own
        assert it.nsfw_locked and it.nsfw_lock_level == "moderator"

    async def test_bulk_add_returns_effective_nsfw(self, session) -> None:
        me = await adult(session)
        m = await make_media(session, me, nsfw=True)
        other = await make_media(session, me)
        alb = await make_album(session, me, nsfw=False, media=other)
        svc = GalleryService(GalleryRepository(session), CID, session)
        (it,) = await svc.bulk_add_items(alb.id, me.id, GalleryItemBulkCreate(media_ids=[m.id]))
        assert it.is_nsfw and it.is_nsfw_own
