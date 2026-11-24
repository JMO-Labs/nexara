"""
@file test_nsfw_contract_fields.py
@brief Real Postgres: the API carries the NSFW fields the UI blurs on
       (gallery item ``is_nsfw``, aggregated ``media.is_nsfw``, album ``cover_is_nsfw``).
"""

from __future__ import annotations

import uuid

from app.models.gallery import Gallery, GalleryItem
from app.models.subgroup import Subgroup, SubgroupMember
from app.repositories.gallery_repo import GalleryRepository
from app.repositories.subgroup_media_repo import SubgroupMediaRepository
from app.services.gallery_service import GalleryService
from tests.integration.repositories.nsfw_fixtures import (
    CID,
    adult,
    attach,
    make_album,
    make_media,
    make_post,
    nsfw_session,  # noqa: F401 - provides the "session" fixture
    teen,
)


class TestGalleryFields:
    async def test_items_carry_is_nsfw(self, session) -> None:
        owner = await adult(session)
        flagged = await make_media(session, owner, nsfw=True)
        via_post = await make_media(session, owner)
        safe = await make_media(session, owner)
        await attach(session, await make_post(session, owner, nsfw=True), via_post)
        g = await make_album(session, owner, nsfw=False, media=flagged)
        for m in (via_post, safe):
            session.add(
                GalleryItem(community_id=CID, gallery_id=g.id, media_id=m.id, added_by=owner.id)
            )
        await session.flush()
        svc = GalleryService(GalleryRepository(session), CID, session)
        got = {i.media_id: i.is_nsfw for i in await svc.list_items(g.id, owner.id)}
        assert got == {flagged.id: True, via_post.id: True, safe.id: False}

    async def test_cover_is_nsfw_for_adults_hidden_for_teens(self, session) -> None:
        owner, kid = await adult(session), await teen(session)
        m = await make_media(session, owner, nsfw=True)
        g = await make_album(session, owner, nsfw=False, media=m)
        g.cover_media_id = m.id
        await session.flush()
        svc = GalleryService(GalleryRepository(session), CID, session)
        grown_view = await svc.get_gallery(g.id, owner.id)
        assert grown_view.cover_is_nsfw is True
        assert grown_view.cover_media_id == m.id
        kid_view = await svc.get_gallery(g.id, kid.id)
        assert kid_view.cover_media_id is None
        assert kid_view.cover_is_nsfw is False


class TestAggregatedFields:
    async def test_community_aggregate_marks_nsfw(self, session) -> None:
        owner = await adult(session)
        flagged = await make_media(session, owner, nsfw=True)
        safe = await make_media(session, owner)
        g = await make_album(session, owner, nsfw=False, media=flagged)
        session.add(
            GalleryItem(community_id=CID, gallery_id=g.id, media_id=safe.id, added_by=owner.id)
        )
        await session.flush()
        rows, _ = await SubgroupMediaRepository(session).list_aggregated(
            community_id=CID, viewer_id=owner.id, limit=200
        )
        got = {r["media_id"]: r["media"]["is_nsfw"] for r in rows}
        assert got[str(flagged.id)] is True
        assert got[str(safe.id)] is False

    async def test_subgroup_media_marks_nsfw(self, session) -> None:
        owner = await adult(session)
        sg = Subgroup(community_id=CID, name="g", slug=f"nc-{uuid.uuid4().hex[:10]}")
        session.add(sg)
        await session.flush()
        session.add(SubgroupMember(community_id=CID, subgroup_id=sg.id, user_id=owner.id))
        flagged = await make_media(session, owner, nsfw=True)
        safe = await make_media(session, owner)
        g = Gallery(
            community_id=CID,
            owner_id=owner.id,
            title="sg album",
            visibility="subgroup",
            subgroup_id=sg.id,
        )
        session.add(g)
        await session.flush()
        for m in (flagged, safe):
            session.add(
                GalleryItem(community_id=CID, gallery_id=g.id, media_id=m.id, added_by=owner.id)
            )
        await session.flush()
        rows, _ = await SubgroupMediaRepository(session).list_media(
            subgroup_id=sg.id, viewer_id=owner.id, source="all", cursor=None, limit=50
        )
        got = {r["media_id"]: r["media"]["is_nsfw"] for r in rows}
        assert got == {str(flagged.id): True, str(safe.id): False}
