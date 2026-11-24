"""
@file test_nsfw_container_locks.py
@brief Real Postgres: a moderator/admin NSFW flag on an album or post also
       flags and locks its photos at the same level, so moving a photo out
       keeps it NSFW; unflagging at that level clears what it set.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.models.media import Media
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.media_repo import MediaRepository
from app.repositories.moderation_repo import ModerationRepository
from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository
from app.repositories.tag_repo import TagRepository
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


async def _state(s: AsyncSession, m: Media) -> tuple[bool, str | None]:
    await s.refresh(m)
    return m.is_nsfw, m.nsfw_lock_level


class TestContainerLocks:
    async def test_admin_album_flag_locks_photos_and_unflag_clears(self, session) -> None:
        owner, admin = await adult(session), await _admin(session)
        m = await make_media(session, owner)
        g = await make_album(session, owner, nsfw=False, media=m)
        svc = _mod(session)
        await svc.set_flag("galleries", g.id, admin, True)
        assert await _state(session, m) == (True, "admin")
        media_svc = MediaService(
            MediaRepository(session), AsyncMock(), MagicMock(), CID,
            tag_repo=TagRepository(session),
        )  # fmt: skip
        with pytest.raises(AuthorizationError):  # uploader cannot clear the photo
            await media_nsfw.set_media_nsfw(media_svc, owner, m.id, False)
        await svc.set_flag("galleries", g.id, admin, False)
        assert await _state(session, m) == (False, None)

    async def test_moderator_post_flag_keeps_stronger_photo_lock(self, session) -> None:
        author, mod, admin = await adult(session), await adult(session), await _admin(session)
        sg = Subgroup(community_id=CID, name="G", slug=f"cl-{mod.id.hex[:10]}")
        session.add(sg)
        await session.flush()
        session.add(SubgroupMember(community_id=CID, subgroup_id=sg.id, user_id=author.id))
        session.add(
            SubgroupMember(community_id=CID, subgroup_id=sg.id, user_id=mod.id, role="moderator")
        )
        await session.flush()
        p = await make_post(session, author, nsfw=False, subgroup_id=sg.id, visibility="subgroup")
        plain, strong = await make_media(session, author), await make_media(session, author)
        await attach(session, p, plain)
        await attach(session, p, strong)
        svc = _mod(session)
        await svc.set_flag("media", strong.id, admin, True)
        await svc.set_flag("posts", p.id, mod, True)
        assert await _state(session, plain) == (True, "moderator")
        assert await _state(session, strong) == (True, "admin")
        await svc.set_flag("posts", p.id, mod, False)  # clears only what it set
        assert await _state(session, plain) == (False, None)
        assert await _state(session, strong) == (True, "admin")

    async def test_owner_flag_does_not_cascade(self, session) -> None:
        owner = await adult(session)
        m = await make_media(session, owner)
        g = await make_album(session, owner, nsfw=False, media=m)
        await _mod(session).set_flag("galleries", g.id, owner, True)
        assert await _state(session, m) == (False, None)
