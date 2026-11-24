"""
@file test_nsfw_flags.py
@brief Real Postgres: who may set/clear NSFW flags (authors, uploaders, album
       owners, group moderators, admins), moderator locks, feature flag off.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, AuthorizationError
from app.models.community import Community
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.comment_repo import CommentRepository, ReactionRepository
from app.repositories.gallery_repo import GalleryRepository
from app.repositories.media_repo import MediaRepository
from app.repositories.moderation_repo import ModerationRepository
from app.repositories.post_repo import PostRepository
from app.schemas.gallery import GalleryUpdate
from app.services.gallery_service import GalleryService
from app.services.media import nsfw as media_nsfw
from app.services.media_service import MediaService
from app.services.nsfw_moderation import NsfwModerationService
from app.services.post_service import PostService
from tests.integration.repositories.nsfw_fixtures import (
    CID,
    adult,
    attach,
    make_album,
    make_media,
    make_post,
    make_user,
    nsfw_session,  # noqa: F401 - provides the "session" fixture
    teen,
)


def _posts(s: AsyncSession) -> PostService:
    return PostService(
        PostRepository(s), CommentRepository(s), ReactionRepository(s), AsyncMock(), CID
    )


def _mod(s: AsyncSession) -> tuple[NsfwModerationService, AsyncMock]:
    audit = AsyncMock()
    return NsfwModerationService(ModerationRepository(s), audit, CID, s, AsyncMock()), audit


async def _group(s: AsyncSession, **roles: User) -> Subgroup:
    sg = Subgroup(community_id=CID, name="G", slug=f"nsfw-{next(iter(roles.values())).id.hex[:8]}")
    s.add(sg)
    await s.flush()
    for role, u in roles.items():
        s.add(SubgroupMember(community_id=CID, subgroup_id=sg.id, user_id=u.id, role=role))
    await s.flush()
    return sg


async def _feature_off(s: AsyncSession) -> None:
    c = await s.get(Community, CID)
    c.features = {**(c.features or {}), "nsfw": False}
    await s.flush()


class TestAuthorLock:
    async def test_author_sets_and_clears_when_unlocked(self, session) -> None:
        me = await adult(session)
        p = await make_post(session, me, nsfw=False)
        await _posts(session).update_post(p.id, me, "x", is_nsfw=True)
        assert p.is_nsfw is True and p.nsfw_locked is False
        await _posts(session).update_post(p.id, me, "x", is_nsfw=False)
        assert p.is_nsfw is False

    async def test_author_cannot_clear_moderator_flag(self, session) -> None:
        me, admin = await adult(session), await make_user(session, age_group="adult")
        admin.role = "admin"
        p = await make_post(session, me, nsfw=False)
        svc, audit = _mod(session)
        await svc.set_flag("posts", p.id, admin, True)
        await session.refresh(p)
        assert p.is_nsfw is True and p.nsfw_locked is True
        assert audit.append.call_args.kwargs["extra_data"] == {"value": True, "lock_level": "admin"}
        with pytest.raises(AuthorizationError):
            await _posts(session).update_post(p.id, me, "x", is_nsfw=False)
        await svc.set_flag("posts", p.id, admin, False)  # moderator unflag clears the lock
        await session.refresh(p)
        assert p.is_nsfw is False and p.nsfw_locked is False

    async def test_feature_off_rejects_new_flags_keeps_old(self, session) -> None:
        me = await adult(session)
        old = await make_post(session, me, nsfw=True)
        await _feature_off(session)
        with pytest.raises(AppError) as exc:
            await _posts(session).create_post(me, "x", is_nsfw=True)
        assert exc.value.code == "FEATURE_DISABLED"
        assert (await _posts(session).get_post(old.id, viewer_id=me.id))["is_nsfw"] is True


class TestGroupModerators:
    async def test_group_moderator_flags_post_in_group(self, session) -> None:
        author, mod, member = await adult(session), await adult(session), await adult(session)
        sg = await _group(session, member=author, moderator=mod)
        session.add(SubgroupMember(community_id=CID, subgroup_id=sg.id, user_id=member.id))
        await session.flush()
        p = await make_post(session, author, nsfw=False, subgroup_id=sg.id, visibility="subgroup")
        svc, _ = _mod(session)
        with pytest.raises(AuthorizationError):
            await svc.set_flag("posts", p.id, member, True)
        await svc.set_flag("posts", p.id, mod, True)
        await session.refresh(p)
        assert p.is_nsfw is True and p.nsfw_locked is True

    async def test_moderator_has_no_power_outside_group(self, session) -> None:
        author, mod = await adult(session), await adult(session)
        await _group(session, moderator=mod)
        p = await make_post(session, author, nsfw=False)
        with pytest.raises(AuthorizationError):
            await _mod(session)[0].set_flag("posts", p.id, mod, True)

    async def test_teen_moderator_may_flag_not_unflag(self, session) -> None:
        author, kid = await adult(session), await teen(session)
        sg = await _group(session, member=author, owner=kid)
        p = await make_post(session, author, nsfw=False, subgroup_id=sg.id, visibility="subgroup")
        svc, _ = _mod(session)
        await svc.set_flag("posts", p.id, kid, True)
        with pytest.raises(AuthorizationError):
            await svc.set_flag("posts", p.id, kid, False)


class TestAlbumsAndPhotos:
    async def test_album_owner_and_admin(self, session) -> None:
        owner, stranger = await adult(session), await adult(session)
        admin = await make_user(session, age_group="adult")
        admin.role = "admin"
        g = await make_album(session, owner, nsfw=False, media=await make_media(session, owner))
        svc, _ = _mod(session)
        with pytest.raises(AuthorizationError):
            await svc.set_flag("galleries", g.id, stranger, True)
        await svc.set_flag("galleries", g.id, owner, True)  # owner rules: no lock
        await session.refresh(g)
        assert g.is_nsfw is True and g.nsfw_locked is False
        await svc.set_flag("galleries", g.id, admin, True)
        await session.refresh(g)
        assert g.nsfw_locked is True
        gallery_svc = GalleryService(GalleryRepository(session), CID, session)
        with pytest.raises(AuthorizationError):
            await gallery_svc.update_gallery(g.id, owner.id, GalleryUpdate(is_nsfw=False))

    def _media_svc(self, s: AsyncSession) -> MediaService:
        return MediaService(MediaRepository(s), AsyncMock(), MagicMock(), CID)

    async def test_uploader_flags_photo(self, session) -> None:
        me, other, kid = await adult(session), await adult(session), await teen(session)
        m = await make_media(session, me)
        await attach(session, await make_post(session, me, nsfw=False), m)  # visible to others
        svc = self._media_svc(session)
        out = await media_nsfw.set_media_nsfw(svc, me, m.id, True)
        assert out.is_nsfw is True
        with pytest.raises(AuthorizationError):
            await media_nsfw.set_media_nsfw(svc, other, m.id, False)
        assert (await media_nsfw.set_media_nsfw(svc, me, m.id, False)).is_nsfw is False
        kid_media = await make_media(session, kid)
        with pytest.raises(AuthorizationError):
            await media_nsfw.set_media_nsfw(svc, kid, kid_media.id, True)
        with pytest.raises(AuthorizationError):
            await media_nsfw.precheck_flag(svc, kid)

    async def test_photo_lock_and_feature_off(self, session) -> None:
        me = await adult(session)
        admin = await make_user(session, age_group="adult")
        admin.role = "admin"
        m = await make_media(session, me)
        await _mod(session)[0].set_flag("media", m.id, admin, True)
        await session.refresh(m)
        svc = self._media_svc(session)
        with pytest.raises(AuthorizationError):
            await media_nsfw.set_media_nsfw(svc, me, m.id, False)
        await _feature_off(session)
        with pytest.raises(AppError):
            await media_nsfw.precheck_flag(svc, me)
