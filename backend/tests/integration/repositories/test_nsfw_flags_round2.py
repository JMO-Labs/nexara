"""
@file test_nsfw_flags_round2.py
@brief Real Postgres regressions: an author who owns/moderates the group cannot
       clear an admin lock through the moderation endpoint; photo PATCH hides
       existence (404) from those who cannot see it; NSFW album covers are
       hidden from non-adults.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.gallery import Gallery
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.gallery_repo import GalleryRepository
from app.repositories.media_repo import MediaRepository
from app.repositories.moderation_repo import ModerationRepository
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
    teen,
)


def _mod(s: AsyncSession) -> NsfwModerationService:
    return NsfwModerationService(ModerationRepository(s), AsyncMock(), CID, s, AsyncMock())


async def _admin(s: AsyncSession) -> User:
    a = await make_user(s, age_group="adult")
    a.role = "admin"
    return a


async def _own_group(s: AsyncSession, owner: User) -> Subgroup:
    sg = Subgroup(community_id=CID, name="Mine", slug=f"own-{owner.id.hex[:10]}")
    s.add(sg)
    await s.flush()
    s.add(SubgroupMember(community_id=CID, subgroup_id=sg.id, user_id=owner.id, role="owner"))
    await s.flush()
    return sg


class TestAuthorAsGroupOwnerAttack:
    async def test_cannot_clear_admin_flag_on_own_post(self, session) -> None:
        me, admin = await adult(session), await _admin(session)
        sg = await _own_group(session, me)
        p = await make_post(session, me, nsfw=False, subgroup_id=sg.id, visibility="subgroup")
        svc = _mod(session)
        await svc.set_flag("posts", p.id, admin, True)
        with pytest.raises(AuthorizationError):
            await svc.set_flag("posts", p.id, me, False)
        await session.refresh(p)
        assert p.is_nsfw is True

    async def test_cannot_clear_admin_flag_on_own_album(self, session) -> None:
        me, admin = await adult(session), await _admin(session)
        sg = await _own_group(session, me)
        g = await make_album(session, me, nsfw=False, media=await make_media(session, me))
        g.subgroup_id, g.visibility = sg.id, "subgroup"
        await session.flush()
        svc = _mod(session)
        await svc.set_flag("galleries", g.id, admin, True)
        with pytest.raises(AuthorizationError):
            await svc.set_flag("galleries", g.id, me, False)
        await session.refresh(g)
        assert g.is_nsfw is True

    async def test_owner_flag_on_own_post_does_not_lock(self, session) -> None:
        me = await adult(session)
        sg = await _own_group(session, me)
        p = await make_post(session, me, nsfw=False, subgroup_id=sg.id, visibility="subgroup")
        svc = _mod(session)
        await svc.set_flag("posts", p.id, me, True)
        await svc.set_flag("posts", p.id, me, False)  # own, unlocked: may clear
        assert p.is_nsfw is False


class TestPhotoPatchExistence:
    def _svc(self, s: AsyncSession) -> MediaService:
        return MediaService(MediaRepository(s), AsyncMock(), MagicMock(), CID)

    async def test_hidden_photo_is_404_visible_not_mine_is_403(self, session) -> None:
        owner, other, kid = await adult(session), await adult(session), await teen(session)
        nsfw = await make_media(session, owner, nsfw=True)
        await attach(session, await make_post(session, owner, nsfw=False), nsfw)
        private = await make_media(session, owner)  # unattached: only the uploader sees it
        safe = await make_media(session, owner)
        await attach(session, await make_post(session, owner, nsfw=False), safe)
        svc = self._svc(session)
        for who, mid in ((kid, nsfw.id), (other, private.id)):
            with pytest.raises(NotFoundError):
                await media_nsfw.set_media_nsfw(svc, who, mid, False)
        for who, mid in ((other, nsfw.id), (kid, safe.id)):
            with pytest.raises(AuthorizationError):
                await media_nsfw.set_media_nsfw(svc, who, mid, True)


class TestAlbumCover:
    async def test_nsfw_cover_hidden_from_teen(self, session) -> None:
        owner, grown, kid = await adult(session), await adult(session), await teen(session)
        cover = await make_media(session, owner, nsfw=True)
        g: Gallery = await make_album(session, owner, nsfw=False, media=cover)
        g.cover_media_id = cover.id
        await session.flush()
        svc = GalleryService(GalleryRepository(session), CID, session)
        assert (await svc.get_gallery(g.id, kid.id)).cover_media_id is None
        assert (await svc.get_gallery(g.id, grown.id)).cover_media_id == cover.id
        teen_list = {
            x.id: x.cover_media_id for x in (await svc.list_galleries(kid.id, limit=200)).items
        }
        assert g.id in teen_list and teen_list[g.id] is None
        adult_list = {
            x.id: x.cover_media_id for x in (await svc.list_galleries(grown.id, limit=200)).items
        }
        assert adult_list[g.id] == cover.id


class TestTaggedPhotos:
    async def test_nsfw_media_ids_only_for_adults(self, session) -> None:
        from app.models.tag import Tag
        from app.repositories.post_repo import PostRepository
        from app.repositories.tag_repo import TagRepository
        from app.services.tag_service import TagService

        subject, grown, kid = await adult(session), await adult(session), await teen(session)
        post = await make_post(session, subject, nsfw=False)
        safe, flagged = await make_media(session, subject), await make_media(session, subject)
        in_album = await make_media(session, subject)
        await make_album(session, subject, nsfw=True, media=in_album)
        flagged.is_nsfw = True
        for m in (safe, flagged, in_album):
            await attach(session, post, m)
            session.add(
                Tag(
                    community_id=CID,
                    target_type="media",
                    target_id=m.id,
                    subject_type="user",
                    subject_id=subject.id,
                    tagged_by=subject.id,
                )
            )
        await session.flush()
        svc = TagService(TagRepository(session), PostRepository(session), AsyncMock(), CID)
        adult_page = await svc.tagged(subject.id, grown, "photos", None)
        teen_page = await svc.tagged(subject.id, kid, "photos", None)
        assert set(adult_page["nsfw_media_ids"]) == {str(flagged.id), str(in_album.id)}
        assert set(adult_page["media_ids"]) == {safe.id, flagged.id, in_album.id}
        assert teen_page["media_ids"] == [safe.id] and teen_page["nsfw_media_ids"] == []


class TestSubgroupCover:
    async def test_nsfw_cover_flagged_for_adults_dropped_for_teens(self, session) -> None:
        from app.repositories.post_repo import PostRepository
        from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository
        from app.schemas.subgroup import SubgroupResponse
        from app.services.subgroups.service import SubgroupService

        owner, grown, kid = await adult(session), await adult(session), await teen(session)
        nsfw_cover, safe_cover = await make_media(session, owner), await make_media(session, owner)
        await attach(session, await make_post(session, owner, nsfw=True), nsfw_cover)
        groups = []
        for cover in (nsfw_cover, safe_cover):
            sg = Subgroup(
                community_id=CID,
                name="C",
                slug=f"cov-{cover.id.hex[:10]}",
                cover_media_id=cover.id,
            )
            session.add(sg)
            groups.append(sg)
        await session.flush()
        for sg in groups:
            await session.refresh(sg)
        svc = SubgroupService(
            SubgroupRepository(session),
            SubgroupMemberRepository(session),
            PostRepository(session),
            CID,
        )

        async def view(u: User) -> list[tuple[object, bool]]:
            items = [SubgroupResponse.model_validate(g) for g in groups]
            await svc.apply_cover_nsfw(items, u.id)
            return [(i.cover_media_id, i.cover_is_nsfw) for i in items]

        assert await view(grown) == [(nsfw_cover.id, True), (safe_cover.id, False)]
        assert await view(kid) == [(None, False), (safe_cover.id, False)]
