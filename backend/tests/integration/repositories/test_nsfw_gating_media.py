"""
@file test_nsfw_gating_media.py
@brief Review-focus, real Postgres: NSFW photos, albums, notifications,
       realtime audience and activity never reach a teen; adults still get them.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.activity_event import ActivityEvent
from app.models.notification import Notification
from app.models.post import Comment
from app.repositories.activity_repo import ActivityRepository
from app.repositories.comment_repo import CommentRepository, ReactionRepository
from app.repositories.gallery_repo import GalleryRepository
from app.repositories.media_repo import MediaRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.post_repo import PostRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.subgroup_media_repo import SubgroupMediaRepository
from app.repositories.tag_repo import TagRepository
from app.schemas.gallery import GalleryCreate
from app.services.gallery_service import GalleryService
from app.services.media_service import MediaService
from app.services.notification_service import NotificationService
from app.services.post_service import PostService
from app.services.realtime.audience import resolve_audience
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


def _media_svc(s: AsyncSession) -> MediaService:
    storage = AsyncMock()
    storage.get.return_value = b"IMG"
    return MediaService(MediaRepository(s), storage, MagicMock(), CID)


async def _assert_media_gated(s: AsyncSession, media_id, kid, grown) -> None:
    svc = _media_svc(s)
    for viewer in (kid.id, None):
        with pytest.raises(NotFoundError):
            await svc.get_file_public(media_id, viewer)
        with pytest.raises(NotFoundError):
            await svc.get_thumbnail(media_id, viewer)
        with pytest.raises(NotFoundError):
            await svc.get_metadata(media_id, viewer)
    assert (await svc.get_file_public(media_id, grown.id))[0] == b"IMG"
    assert (await svc.get_thumbnail(media_id, grown.id))[0] == b"IMG"
    assert (await svc.get_metadata(media_id, grown.id)).id == media_id


class TestMediaFiles:
    async def test_media_in_nsfw_album(self, session) -> None:
        owner, grown, kid = await adult(session), await adult(session), await teen(session)
        m = await make_media(session, owner)
        await make_album(session, owner, nsfw=True, media=m)
        await _assert_media_gated(session, m.id, kid, grown)

    async def test_media_in_nsfw_post(self, session) -> None:
        owner, grown, kid = await adult(session), await adult(session), await teen(session)
        m = await make_media(session, owner)
        await attach(session, await make_post(session, owner, nsfw=True), m)
        await _assert_media_gated(session, m.id, kid, grown)

    async def test_flagged_media_and_unknown_age(self, session) -> None:
        owner, grown, unknown = await adult(session), await adult(session), await make_user(session)
        m = await make_media(session, owner, nsfw=True)
        await _assert_media_gated(session, m.id, unknown, grown)

    async def test_safe_media_served_to_teen(self, session) -> None:
        owner, kid = await adult(session), await teen(session)
        m = await make_media(session, owner)
        assert (await _media_svc(session).get_file_public(m.id, kid.id))[0] == b"IMG"


class TestAlbums:
    async def test_album_hidden_from_teen(self, session) -> None:
        owner, grown, kid = await adult(session), await adult(session), await teen(session)
        g = await make_album(session, owner, nsfw=True, media=await make_media(session, owner))
        repo = GalleryRepository(session)
        svc = GalleryService(repo, CID, session)
        teen_list, _ = await repo.list_visible(CID, viewer_id=kid.id, limit=200)
        adult_list, _ = await repo.list_visible(CID, viewer_id=grown.id, limit=200)
        assert g.id not in {x.id for x in teen_list}
        assert g.id in {x.id for x in adult_list}
        agg, _ = await repo.list_aggregated(CID, viewer_id=kid.id, limit=200)
        assert g.id not in {x.id for x in agg}
        with pytest.raises(NotFoundError):
            await svc.get_gallery(g.id, kid.id)
        with pytest.raises(NotFoundError):
            await svc.list_items(g.id, kid.id)
        assert (await svc.get_gallery(g.id, grown.id)).is_nsfw is True
        assert len(await svc.list_items(g.id, grown.id)) == 1

    async def test_nsfw_photo_in_safe_album_and_media_lists(self, session) -> None:
        owner, grown, kid = await adult(session), await adult(session), await teen(session)
        m = await make_media(session, owner, nsfw=True)
        g = await make_album(session, owner, nsfw=False, media=m)
        svc = GalleryService(GalleryRepository(session), CID, session)
        assert await svc.list_items(g.id, kid.id) == []
        assert len(await svc.list_items(g.id, grown.id)) == 1
        media = SubgroupMediaRepository(session)
        teen_rows, _ = await media.list_aggregated(community_id=CID, viewer_id=kid.id, limit=200)
        adult_rows, _ = await media.list_aggregated(community_id=CID, viewer_id=grown.id, limit=200)
        assert str(m.id) not in {r["media_id"] for r in teen_rows}
        assert str(m.id) in {r["media_id"] for r in adult_rows}
        tags = TagRepository(session)
        assert await tags.media_viewable(m.id, kid.id, CID) is False
        assert await tags.media_viewable(m.id, grown.id, CID) is True

    async def test_teen_cannot_create_nsfw_album(self, session) -> None:
        kid = await teen(session)
        svc = GalleryService(GalleryRepository(session), CID, session)
        with pytest.raises(AuthorizationError):
            await svc.create_gallery(kid.id, GalleryCreate(title="x", is_nsfw=True))


class TestNotifications:
    def _notif(self, s: AsyncSession) -> NotificationService:
        return NotificationService(
            NotificationRepository(s), SettingsRepository(s), CID, dispatcher=AsyncMock()
        )

    async def _rows(self, s: AsyncSession, user_id) -> list[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        return list((await s.execute(stmt)).scalars().all())

    async def test_comment_notifies_only_adults(self, session) -> None:
        author, replier, kid = await adult(session), await adult(session), await teen(session)
        p = await make_post(session, author, nsfw=False)
        kid_comment = Comment(community_id=CID, post_id=p.id, author_id=kid.id, content="first")
        session.add(kid_comment)
        p.is_nsfw = True  # flagged after the teen commented
        await session.flush()
        notif = self._notif(session)
        svc = PostService(
            PostRepository(session),
            CommentRepository(session),
            ReactionRepository(session),
            notif,
            CID,
        )
        await svc.add_comment(p.id, replier, "reply", parent_id=kid_comment.id)
        assert len(await self._rows(session, author.id)) == 1
        assert await self._rows(session, kid.id) == []
        notif._dispatcher.dispatch.assert_awaited_once()  # push/email only for the adult

    async def test_direct_notify_skipped_for_teen(self, session) -> None:
        author, kid = await adult(session), await teen(session)
        p = await make_post(session, author, nsfw=True)
        payload = {"post_id": str(p.id), "actor_name": "A", "message": "m", "link": "/x"}
        assert await self._notif(session).notify(kid.id, "comment", payload) is None
        assert await self._notif(session).notify(author.id, "comment", payload) is not None

    async def test_existing_notifications_hidden_in_list(self, session) -> None:
        author, kid = await adult(session), await teen(session)
        p = await make_post(session, author, nsfw=False)
        payload = {"post_id": str(p.id), "actor_name": "A", "message": "m", "link": "/x"}
        await self._notif(session).notify(kid.id, "comment", payload)
        p.is_nsfw = True
        await session.flush()
        listed = await self._notif(session).list_for_user(kid.id)
        assert listed.items == []
        assert await NotificationRepository(session).list_active(kid.id) == []


class TestRealtimeAndActivity:
    async def test_audience_adults_only(self, session) -> None:
        author, grown, kid = await adult(session), await adult(session), await teen(session)
        aud = await resolve_audience(
            session,
            CID,
            visibility="community",
            subgroup_id=None,
            author_id=author.id,
            adults_only=True,
        )
        assert author.id in aud and grown.id in aud and kid.id not in aud

    async def test_activity_feed_omits_nsfw(self, session) -> None:
        author, grown, kid = await adult(session), await adult(session), await teen(session)
        p = await make_post(session, author, nsfw=True)
        session.add(
            ActivityEvent(
                community_id=CID,
                actor_id=author.id,
                verb="post.created",
                object_type="post",
                object_id=p.id,
                visibility="community",
                event_metadata={"object_title": p.content},
                is_active=True,
            )
        )
        await session.flush()
        repo = ActivityRepository(session)

        async def seen(u) -> bool:
            rows = await repo.list_for_user(
                community_id=CID, viewer_id=u.id, viewer_subgroup_ids=[], limit=200
            )
            return p.id in {r.object_id for r in rows}

        assert await seen(kid) is False
        assert await seen(grown) is True
