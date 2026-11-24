"""
@file test_nsfw_update_paths.py
@brief Real Postgres: a non-adult editing their own NSFW-hidden post or album
       gets 404, and album responses never carry an NSFW cover id for them.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.gallery import Gallery
from app.repositories.comment_repo import CommentRepository, ReactionRepository
from app.repositories.gallery_repo import GalleryRepository
from app.repositories.post_repo import PostRepository
from app.schemas.gallery import GalleryUpdate
from app.services.gallery_service import GalleryService
from app.services.post_service import PostService
from tests.integration.repositories.nsfw_fixtures import (
    CID,
    adult,
    make_album,
    make_media,
    make_post,
    nsfw_session,  # noqa: F401 - provides the "session" fixture
    teen,
)


def _posts(s: AsyncSession) -> PostService:
    return PostService(
        PostRepository(s), CommentRepository(s), ReactionRepository(s), AsyncMock(), CID
    )


class TestTeenUpdates:
    async def test_teen_edit_of_own_nsfw_post_is_404(self, session) -> None:
        kid = await teen(session)
        p = await make_post(session, kid, nsfw=True, content="before")
        with pytest.raises(NotFoundError):
            await _posts(session).update_post(p.id, kid, "after")
        await session.refresh(p)
        assert p.content == "before"

    async def test_teen_edit_of_own_nsfw_album_is_404(self, session) -> None:
        kid = await teen(session)
        g = await make_album(session, kid, nsfw=True, media=await make_media(session, kid))
        svc = GalleryService(GalleryRepository(session), CID, session)
        with pytest.raises(NotFoundError):
            await svc.update_gallery(g.id, kid.id, GalleryUpdate(title="renamed"))

    async def test_teen_album_update_drops_nsfw_cover(self, session) -> None:
        kid, grown = await teen(session), await adult(session)
        cover = await make_media(session, grown, nsfw=True)
        g: Gallery = await make_album(session, kid, nsfw=False, media=cover)
        g.cover_media_id = cover.id
        await session.flush()
        svc = GalleryService(GalleryRepository(session), CID, session)
        out = await svc.update_gallery(g.id, kid.id, GalleryUpdate(title="renamed"))
        assert out.title == "renamed" and out.cover_media_id is None
