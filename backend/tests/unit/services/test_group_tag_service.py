"""
@file test_group_tag_service.py
@brief @group tag rules (who may tag which group on which post) and fan-out.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.repositories.group_tag_repo import GroupTagRepository
from app.services.group_tag_service import GroupTagService
from app.services.notification_service import NotificationService

CID = uuid.uuid4()


def _group(policy: str = "members") -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), slug="book-club", name="Book club", tag_policy=policy)


def _svc(groups, roles):
    repo = AsyncMock(spec=GroupTagRepository)
    repo.by_slugs.return_value = groups
    repo.roles.return_value = roles
    return GroupTagService(repo, CID), repo


def _post(visibility: str = "community", subgroup_id=None) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), visibility=visibility, subgroup_id=subgroup_id)


ACTOR = SimpleNamespace(id=uuid.uuid4(), role="member", display_name="Ruth")


async def test_member_tags_group_on_community_post() -> None:
    g = _group()
    svc, _ = _svc([g], {g.id: "member"})
    assert await svc.taggable(["book-club"], ACTOR, _post()) == [g]


async def test_non_member_cannot_tag() -> None:
    g = _group()
    svc, _ = _svc([g], {})
    assert await svc.taggable(["book-club"], ACTOR, _post()) == []


async def test_admins_policy_needs_owner_or_moderator() -> None:
    g = _group("admins")
    svc, _ = _svc([g], {g.id: "member"})
    assert await svc.taggable(["book-club"], ACTOR, _post()) == []
    svc, _ = _svc([g], {g.id: "moderator"})
    assert await svc.taggable(["book-club"], ACTOR, _post()) == [g]


async def test_private_post_tags_nothing() -> None:
    g = _group()
    svc, repo = _svc([g], {g.id: "owner"})
    assert await svc.taggable(["book-club"], ACTOR, _post("private")) == []
    repo.by_slugs.assert_not_awaited()


async def test_group_post_only_tags_its_own_group() -> None:
    own, other = _group(), _group()
    svc, _ = _svc([own, other], {own.id: "member", other.id: "member"})
    post = _post("subgroup", own.id)
    assert await svc.taggable(["a", "b"], ACTOR, post) == [own]


async def test_community_admin_tags_any_group() -> None:
    g = _group("admins")
    svc, _ = _svc([g], {})
    admin = SimpleNamespace(id=uuid.uuid4(), role="admin", display_name="Admin")
    assert await svc.taggable(["book-club"], admin, _post()) == [g]


async def test_fan_out_notifies_each_recipient() -> None:
    g = _group()
    svc, repo = _svc([g], {})
    repo.get.return_value = g
    a, b = uuid.uuid4(), uuid.uuid4()
    repo.recipients.return_value = [a, b]
    notifier = MagicMock(spec=NotificationService)
    notifier.notify = AsyncMock()
    post_id = uuid.uuid4()
    n = await svc.fan_out(notifier, g.id, post_id, ACTOR.id, "Ruth", False)
    assert n == 2
    sent = [c.kwargs for c in notifier.notify.await_args_list]
    assert {s["user_id"] for s in sent} == {a, b}
    assert all(s["type"] == "group_tag" for s in sent)
    assert sent[0]["payload"]["link"] == f"/app/post/{post_id}"
    assert sent[0]["payload"]["message"] == "Ruth tagged Book club in a post"
    repo.recipients.assert_awaited_once_with(g.id, CID, ACTOR.id)


async def test_fan_out_missing_group_is_noop() -> None:
    svc, repo = _svc([], {})
    repo.get.return_value = None
    notifier = MagicMock(spec=NotificationService)
    notifier.notify = AsyncMock()
    assert await svc.fan_out(notifier, uuid.uuid4(), uuid.uuid4(), ACTOR.id, "R", True) == 0
    notifier.notify.assert_not_awaited()
