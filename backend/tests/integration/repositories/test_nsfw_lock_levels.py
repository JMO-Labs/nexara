"""
@file test_nsfw_lock_levels.py
@brief Real Postgres: tiered NSFW locks. Admin flag -> 'admin', group moderator
       -> 'moderator'; clearing needs actor level >= stored level; re-flagging
       never downgrades a lock; lock state is exposed in responses.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.gallery_repo import GalleryRepository
from app.repositories.moderation_repo import ModerationRepository
from app.repositories.post_enrichment import enrich_posts
from app.services.gallery_service import GalleryService
from app.services.nsfw_moderation import NsfwModerationService
from tests.integration.repositories.nsfw_fixtures import (
    CID,
    adult,
    make_album,
    make_media,
    make_post,
    make_user,
    nsfw_session,  # noqa: F401 - provides the "session" fixture
)


def _mod(s: AsyncSession) -> tuple[NsfwModerationService, AsyncMock]:
    audit = AsyncMock()
    return NsfwModerationService(ModerationRepository(s), audit, CID, s, AsyncMock()), audit


async def _admin(s: AsyncSession) -> User:
    a = await make_user(s, age_group="adult")
    a.role = "admin"
    return a


async def _group_post(s: AsyncSession) -> tuple[User, User, object]:
    author, mod = await adult(s), await adult(s)
    sg = Subgroup(community_id=CID, name="G", slug=f"lvl-{mod.id.hex[:10]}")
    s.add(sg)
    await s.flush()
    s.add(SubgroupMember(community_id=CID, subgroup_id=sg.id, user_id=author.id))
    s.add(SubgroupMember(community_id=CID, subgroup_id=sg.id, user_id=mod.id, role="moderator"))
    await s.flush()
    p = await make_post(s, author, nsfw=False, subgroup_id=sg.id, visibility="subgroup")
    return author, mod, p


class TestLockLevels:
    async def test_moderator_cannot_clear_admin_lock(self, session) -> None:
        _author, mod, p = await _group_post(session)
        admin = await _admin(session)
        svc, audit = _mod(session)
        await svc.set_flag("posts", p.id, admin, True)
        assert audit.append.call_args.kwargs["extra_data"] == {"value": True, "lock_level": "admin"}
        with pytest.raises(AuthorizationError):
            await svc.set_flag("posts", p.id, mod, False)
        await svc.set_flag("posts", p.id, mod, True)  # re-flag keeps the admin lock
        await session.refresh(p)
        assert (p.is_nsfw, p.nsfw_lock_level) == (True, "admin")

    async def test_moderator_lock_cleared_by_moderator_or_admin(self, session) -> None:
        _author, mod, p = await _group_post(session)
        admin = await _admin(session)
        svc, _ = _mod(session)
        await svc.set_flag("posts", p.id, mod, True)
        await session.refresh(p)
        assert p.nsfw_lock_level == "moderator" and p.nsfw_locked is True
        await svc.set_flag("posts", p.id, admin, True)  # admin upgrades the lock
        await session.refresh(p)
        assert p.nsfw_lock_level == "admin"
        await svc.set_flag("posts", p.id, admin, False)
        await session.refresh(p)
        assert (p.is_nsfw, p.nsfw_lock_level) == (False, None)
        await svc.set_flag("posts", p.id, mod, True)
        await svc.set_flag("posts", p.id, mod, False)
        await session.refresh(p)
        assert (p.is_nsfw, p.nsfw_lock_level) == (False, None)

    async def test_lock_state_in_responses(self, session) -> None:
        author, mod, p = await _group_post(session)
        svc, _ = _mod(session)
        await svc.set_flag("posts", p.id, mod, True)
        await session.refresh(p)
        data = (await enrich_posts(session, [p.id], author.id))[p.id]
        assert (data["nsfw_locked"], data["nsfw_lock_level"]) == (True, "moderator")
        owner, admin = await adult(session), await _admin(session)
        g = await make_album(session, owner, nsfw=False, media=await make_media(session, owner))
        await svc.set_flag("galleries", g.id, admin, True)
        await session.refresh(g)
        out = await GalleryService(GalleryRepository(session), CID, session).get_gallery(
            g.id, owner.id
        )
        assert (out.nsfw_locked, out.nsfw_lock_level) == (True, "admin")
