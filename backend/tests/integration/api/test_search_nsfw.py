"""
@file test_search_nsfw.py
@brief Tests for NSFW filtering in search and the moderation service.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.media import Media
from app.models.post import Post
from app.models.user import User
from app.services.moderation_service import ModerationService
from app.services.search_service import SearchService, is_adult

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _user(birthday: date | None) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.birthday = birthday
    return u


def _post(nsfw: bool) -> MagicMock:
    p = MagicMock(spec=Post)
    p.id = uuid.uuid4()
    p.content = "hello world"
    p.created_at = datetime.now(UTC)
    p.is_nsfw = nsfw
    return p


ADULT = date(1980, 1, 1)
MINOR = date(date.today().year - 10, 1, 1)


class TestModels:
    def test_models_have_is_nsfw(self):
        assert Post.__table__.c.is_nsfw.nullable is False
        assert Media.__table__.c.is_nsfw.nullable is False


class TestIsAdult:
    def test_adult(self):
        assert is_adult(_user(ADULT)) is True

    def test_minor(self):
        assert is_adult(_user(MINOR)) is False

    def test_no_birthday_not_adult(self):
        assert is_adult(_user(None)) is False


class TestSearchNsfw:
    async def test_non_adult_excludes_nsfw(self):
        repo = AsyncMock()
        repo.search_posts.return_value = ([], None, 0)
        await SearchService(repo, CID).search("hello", _user(MINOR), ["posts"], None, 20)
        assert repo.search_posts.await_args.kwargs["include_nsfw"] is False

    async def test_adult_includes_nsfw_and_flags_items(self):
        repo = AsyncMock()
        repo.search_posts.return_value = ([(_post(True), 0.5), (_post(False), 0.4)], None, 2)
        resp = await SearchService(repo, CID).search("hello", _user(ADULT), ["posts"], None, 20)
        assert repo.search_posts.await_args.kwargs["include_nsfw"] is True
        assert [i.is_nsfw for i in resp.results["posts"].items] == [True, False]


class TestModerationService:
    @pytest.mark.parametrize("kind,model", [("posts", Post), ("media", Media)])
    async def test_mark_nsfw_audits_and_invalidates(self, kind, model):
        entity = MagicMock(spec=model)
        entity.is_nsfw = False
        session = AsyncMock()
        session.get.return_value = entity
        entity.community_id = CID
        entity.deleted_at = None
        audit = AsyncMock()
        invalidate = AsyncMock()
        svc = ModerationService(session, audit, CID, invalidate=invalidate)
        admin = uuid.uuid4()
        await svc.mark_nsfw(kind, uuid.uuid4(), admin)
        assert entity.is_nsfw is True
        audit.append.assert_awaited_once()
        assert audit.append.await_args.kwargs["action"] == f"{kind}.marked_nsfw"
        invalidate.assert_awaited_once()

    async def test_missing_entity_raises(self):
        from app.core.exceptions import NotFoundError

        session = AsyncMock()
        session.get.return_value = None
        svc = ModerationService(session, AsyncMock(), CID, invalidate=AsyncMock())
        with pytest.raises(NotFoundError):
            await svc.mark_nsfw("posts", uuid.uuid4(), uuid.uuid4())
