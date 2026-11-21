"""
@file test_tag_service.py
@brief TagService: photo tagging rules, removal rights, Tagged feed gating.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.models.tag import Tag
from app.models.user import User
from app.repositories.post_repo import PostRepository
from app.repositories.tag_repo import TagRepository
from app.services.tag_service import TagService

CID = uuid.uuid4()


def _user(role: str = "member") -> MagicMock:
    u = MagicMock(spec=User)
    u.id, u.role, u.display_name = uuid.uuid4(), role, "Actor"
    return u


def _svc():
    repo = AsyncMock(spec=TagRepository)
    posts = AsyncMock(spec=PostRepository)
    posts._session = AsyncMock()
    notify = AsyncMock()
    repo.media_uploader.return_value = uuid.uuid4()
    repo.media_viewable.return_value = True
    repo.users_by_ids.return_value = [MagicMock()]
    repo.blocked_with.return_value = set()
    repo.add.return_value = True
    repo.list_for_target.return_value = []
    return TagService(repo, posts, notify, CID), repo, posts, notify


async def test_tag_photo_notifies_once():
    svc, repo, _, notify = _svc()
    actor, target = _user(), uuid.uuid4()
    await svc.tag_media(uuid.uuid4(), target, actor)
    notify.notify.assert_awaited_once()
    assert notify.notify.await_args.kwargs["user_id"] == target
    repo.add.return_value = False  # already tagged
    await svc.tag_media(uuid.uuid4(), target, actor)
    assert notify.notify.await_count == 1


async def test_cannot_tag_in_photo_you_cannot_see():
    svc, repo, _, _ = _svc()
    repo.media_viewable.return_value = False
    with pytest.raises(NotFoundError):
        await svc.tag_media(uuid.uuid4(), uuid.uuid4(), _user())


async def test_cannot_tag_someone_who_cannot_see_it_or_is_blocked():
    svc, repo, _, _ = _svc()
    actor = _user()
    repo.media_viewable.side_effect = lambda _m, who: who == actor.id
    with pytest.raises(ValidationError):
        await svc.tag_media(uuid.uuid4(), uuid.uuid4(), actor)
    repo.media_viewable.side_effect = None
    repo.blocked_with.return_value = {uuid.uuid4()}
    with pytest.raises(ValidationError):
        await svc.tag_media(uuid.uuid4(), uuid.uuid4(), actor)
    repo.add.assert_not_awaited()


def _tag(subject, by, target_type="media"):
    t = MagicMock(spec=Tag)
    t.subject_id, t.tagged_by, t.target_type, t.target_id = subject, by, target_type, uuid.uuid4()
    return t


async def test_remove_rights():
    svc, repo, _, _ = _svc()
    me, other, uploader = _user(), _user(), uuid.uuid4()
    repo.media_uploader.return_value = uploader
    repo.get.return_value = _tag(me.id, other.id)
    await svc.remove(uuid.uuid4(), me)  # tagged person
    repo.get.return_value = _tag(other.id, me.id)
    await svc.remove(uuid.uuid4(), me)  # tagger
    repo.get.return_value = _tag(other.id, other.id)
    with pytest.raises(AuthorizationError):
        await svc.remove(uuid.uuid4(), me)
    await svc.remove(uuid.uuid4(), _user("admin"))
    stranger_owner = _user()
    stranger_owner.id = uploader
    await svc.remove(uuid.uuid4(), stranger_owner)  # photo owner
    assert repo.remove.await_count == 4


async def test_list_hidden_target_404_and_blocked_people_filtered():
    svc, repo, posts, _ = _svc()
    posts.is_visible.return_value = False
    with pytest.raises(NotFoundError):
        await svc.list_for("post", uuid.uuid4(), _user())
    posts.is_visible.return_value = True
    a, b = uuid.uuid4(), uuid.uuid4()
    repo.list_for_target.return_value = [{"user": {"id": a}}, {"user": {"id": b}}]
    repo.blocked_with.return_value = {b}
    out = await svc.list_for("post", uuid.uuid4(), _user())
    assert [t["user"]["id"] for t in out] == [a]


async def test_tagged_feed_blocked_404_and_paging():
    svc, repo, posts, _ = _svc()
    viewer = _user()
    repo.blocked_with.return_value = {uuid.uuid4()}
    with pytest.raises(NotFoundError):
        await svc.tagged(uuid.uuid4(), viewer, "posts", None)
    repo.blocked_with.return_value = set()
    pid = uuid.uuid4()
    repo.tagged_post_ids.return_value = [(pid, datetime.now(UTC))]
    with patch("app.services.tag_service.enrich_posts", AsyncMock(return_value={pid: {"id": pid}})):
        page = await svc.tagged(uuid.uuid4(), viewer, "posts", None)
    assert page["posts"] == [{"id": pid}] and page["next_before"] is None
