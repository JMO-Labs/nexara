"""
@file test_nsfw_container_locks.py
@brief Real Postgres: a moderator/admin NSFW flag on an album or post reaches
       its photos via source rows (moving a photo out keeps it NSFW and
       locked); unflagging removes only that container's sources.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.models.gallery import Gallery, GalleryItem
from app.models.media import Media
from app.models.post import PostMedia
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.gallery_repo import GalleryRepository
from app.repositories.media_repo import MediaRepository
from app.repositories.moderation_repo import ModerationRepository
from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository
from app.repositories.tag_repo import TagRepository
from app.schemas.gallery import GalleryItemBulkCreate, GalleryItemCreate
from app.services.gallery_service import GalleryService
from app.services.media import nsfw as media_nsfw
from app.services.media_service import MediaService
from app.services.nsfw_moderation import NsfwModerationService
from tests.integration.repositories.nsfw_fixtures import (
    CID,
    adult,
    attach,
    make_album,
    make_media,
    make_post,
    make_user,
    nsfw_session,  # noqa: F401 - provides the "session" fixture
)


def _mod(s: AsyncSession) -> NsfwModerationService:
    return NsfwModerationService(
        ModerationRepository(s),
        AsyncMock(),
        CID,
        s,
        AsyncMock(),
        groups=SubgroupRepository(s),
        members=SubgroupMemberRepository(s),
    )


async def _admin(s: AsyncSession) -> User:
    a = await make_user(s, age_group="adult")
    a.role = "admin"
    return a


def _media_svc(s: AsyncSession) -> MediaService:
    return MediaService(
        MediaRepository(s), AsyncMock(), MagicMock(), CID, tag_repo=TagRepository(s)
    )


async def _state(s: AsyncSession, m: Media) -> tuple[bool, str | None]:
    """@brief (effective NSFW, effective lock level)."""
    repo = MediaRepository(s)
    await s.refresh(m)
    lock = await repo.nsfw_source_level(m.id)
    own = m.nsfw_lock_level
    level = "admin" if "admin" in (own, lock) else (own or lock)
    return await _media_svc(s).is_nsfw(m.id), level


async def _album(s: AsyncSession, owner: User, *media: Media) -> Gallery:
    g = await make_album(s, owner, nsfw=False, media=media[0])
    for m in media[1:]:
        s.add(GalleryItem(community_id=CID, gallery_id=g.id, media_id=m.id, added_by=owner.id))
    await s.flush()
    return g


async def _group(s: AsyncSession, *members: User, mod: User) -> Subgroup:
    sg = Subgroup(community_id=CID, name="G", slug=f"cl-{uuid.uuid4().hex[:10]}")
    s.add(sg)
    await s.flush()
    for u in members:
        s.add(SubgroupMember(community_id=CID, subgroup_id=sg.id, user_id=u.id))
    s.add(SubgroupMember(community_id=CID, subgroup_id=sg.id, user_id=mod.id, role="moderator"))
    await s.flush()
    return sg


class TestContainerLocks:
    async def test_moved_out_photo_stays_locked_until_unflag(self, session) -> None:
        owner, admin = await adult(session), await _admin(session)
        m = await make_media(session, owner)
        g = await _album(session, owner, m)
        svc = _mod(session)
        await svc.set_flag("galleries", g.id, admin, True)
        await session.execute(delete(GalleryItem).where(GalleryItem.gallery_id == g.id))
        assert await _state(session, m) == (True, "admin")  # moved out: still NSFW
        with pytest.raises(AuthorizationError):  # uploader cannot clear it
            await media_nsfw.set_media_nsfw(_media_svc(session), owner, m.id, False)
        await svc.set_flag("galleries", g.id, admin, False)
        assert await _state(session, m) == (False, None)

    async def test_photo_in_two_flagged_albums_survives_one_unflag(self, session) -> None:
        owner, admin = await adult(session), await _admin(session)
        m = await make_media(session, owner)
        a, b = await _album(session, owner, m), await _album(session, owner, m)
        svc = _mod(session)
        await svc.set_flag("galleries", a.id, admin, True)
        await svc.set_flag("galleries", b.id, admin, True)
        await session.execute(delete(GalleryItem).where(GalleryItem.media_id == m.id))
        await svc.set_flag("galleries", a.id, admin, False)
        assert await _state(session, m) == (True, "admin")

    async def test_directly_flagged_photo_kept_after_container_unflag(self, session) -> None:
        owner, admin = await adult(session), await _admin(session)
        m = await make_media(session, owner)
        g = await _album(session, owner, m)
        svc = _mod(session)
        await svc.set_flag("media", m.id, admin, True)
        await svc.set_flag("galleries", g.id, admin, True)
        await svc.set_flag("galleries", g.id, admin, False)
        assert await _state(session, m) == (True, "admin")

    async def test_moderator_reaches_only_authors_own_photos(self, session) -> None:
        author, other, mod = await adult(session), await adult(session), await adult(session)
        sg = await _group(session, author, other, mod=mod)
        p = await make_post(session, author, nsfw=False, subgroup_id=sg.id, visibility="subgroup")
        mine, theirs = await make_media(session, author), await make_media(session, other)
        await attach(session, p, mine)
        await attach(session, p, theirs)
        await _mod(session).set_flag("posts", p.id, mod, True)
        await session.execute(delete(PostMedia).where(PostMedia.post_id == p.id))
        assert await _state(session, mine) == (True, "moderator")
        assert await _state(session, theirs) == (False, None)

    async def test_moderator_unflag_keeps_admin_photo_lock(self, session) -> None:
        author, mod, admin = await adult(session), await adult(session), await _admin(session)
        sg = await _group(session, author, mod=mod)
        p = await make_post(session, author, nsfw=False, subgroup_id=sg.id, visibility="subgroup")
        plain, strong = await make_media(session, author), await make_media(session, author)
        await attach(session, p, plain)
        await attach(session, p, strong)
        svc = _mod(session)
        await svc.set_flag("media", strong.id, admin, True)
        await svc.set_flag("posts", p.id, mod, True)
        await svc.set_flag("posts", p.id, mod, False)
        assert await _state(session, plain) == (False, None)
        assert await _state(session, strong) == (True, "admin")

    async def test_owner_flag_does_not_cascade(self, session) -> None:
        owner = await adult(session)
        m = await make_media(session, owner)
        g = await _album(session, owner, m)
        await _mod(session).set_flag("galleries", g.id, owner, True)
        await session.execute(delete(GalleryItem).where(GalleryItem.gallery_id == g.id))
        assert await _state(session, m) == (False, None)


class TestAlbumAdds:
    async def test_cannot_add_someone_elses_photo_unless_admin(self, session) -> None:
        owner, other, admin = await adult(session), await adult(session), await _admin(session)
        g = await _album(session, owner, await make_media(session, owner))
        g.contribution_policy = "community"
        await session.flush()
        theirs = await make_media(session, other)
        svc = GalleryService(GalleryRepository(session), CID, session)
        with pytest.raises(AuthorizationError):
            await svc.add_item(g.id, owner.id, GalleryItemCreate(media_id=theirs.id))
        with pytest.raises(AuthorizationError):
            await svc.bulk_add_items(g.id, owner.id, GalleryItemBulkCreate(media_ids=[theirs.id]))
        assert (await svc.add_item(g.id, admin.id, GalleryItemCreate(media_id=theirs.id))).media_id
