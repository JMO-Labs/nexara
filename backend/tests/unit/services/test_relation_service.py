"""
@file test_relation_service.py
@brief Unit tests for RelationService (AsyncMock repos).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, AuthorizationError, ConflictError, NotFoundError
from app.models.community import Community
from app.models.household import HouseholdMember
from app.models.relation import Relation
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.community_repo import CommunityRepository
from app.repositories.household_repo import HouseholdRepository
from app.repositories.profile_repo import ProfileRepository
from app.repositories.relation_repo import RelationRepository
from app.services.notification_service import NotificationService
from app.services.relation_service import RelationService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
RUTH, DANA, MAYA = (uuid.UUID(int=i) for i in (1, 2, 3))


def _user(uid, name="X", role="member", pronouns=None, memorial=None):
    u = MagicMock(spec=User)
    u.id, u.role, u.display_name, u.username = uid, role, name, name.lower()
    u.pronouns, u.avatar_url, u.memorialized_at = pronouns, None, memorial
    return u


def _rel(frm, to, kind="child", status="pending"):
    r = MagicMock(spec=Relation)
    r.id, r.from_user_id, r.to_user_id, r.kind = uuid.uuid4(), frm, to, kind
    r.to_household_member_id, r.label, r.status = None, None, status
    return r


@pytest.fixture
def parts():
    comm = AsyncMock(spec=CommunityRepository)
    c = MagicMock(spec=Community)
    c.features = {}
    comm.get.return_value = c
    p = {
        "repo": AsyncMock(spec=RelationRepository),
        "profiles": AsyncMock(spec=ProfileRepository),
        "household": AsyncMock(spec=HouseholdRepository),
        "communities": comm,
        "notifications": AsyncMock(spec=NotificationService),
    }
    p["profiles"].blocked_either_way.return_value = False
    p["repo"].pair_exists.return_value = False
    return p


@pytest.fixture
def svc(parts):
    return RelationService(community_id=CID, **parts)


async def test_request_stores_inverse_and_notifies(svc, parts):
    ruth, dana = _user(RUTH, "Ruth", pronouns="she/her"), _user(DANA, "Dana")
    parts["repo"].users_visible.return_value = {RUTH: ruth}
    parts["repo"].create.return_value = _rel(DANA, RUTH)
    # Dana: "Ruth is my parent" -> stored Dana is child of Ruth
    await svc.request(dana, to_user_id=RUTH, kind="parent")
    kw = parts["repo"].create.call_args.kwargs
    assert (kw["from_user_id"], kw["to_user_id"], kw["kind"], kw["status"]) == (
        DANA,
        RUTH,
        "child",
        "pending",
    )
    n = parts["notifications"].notify.call_args.args
    assert n[0] == RUTH and n[1] == "relation_request"
    assert "Dana says you are their mother" in n[2]["message"]


async def test_request_blocked_or_unknown_is_not_found_and_silent(svc, parts):
    parts["repo"].users_visible.return_value = {}
    with pytest.raises(NotFoundError):
        await svc.request(_user(DANA), to_user_id=RUTH, kind="friend")
    parts["notifications"].notify.assert_not_called()


async def test_request_memorialized_target_rejected(svc, parts):
    parts["repo"].users_visible.return_value = {RUTH: _user(RUTH, memorial=object())}
    with pytest.raises(AppError):
        await svc.request(_user(DANA), to_user_id=RUTH, kind="parent")
    parts["repo"].create.assert_not_called()


async def test_reverse_duplicate_is_409(svc, parts):
    parts["repo"].users_visible.return_value = {RUTH: _user(RUTH)}
    parts["repo"].pair_exists.return_value = True
    with pytest.raises(ConflictError):
        await svc.request(_user(DANA), to_user_id=RUTH, kind="parent")


async def test_unique_race_is_409(svc, parts):
    parts["repo"].users_visible.return_value = {RUTH: _user(RUTH)}
    parts["repo"].create.return_value = None
    with pytest.raises(ConflictError):
        await svc.request(_user(DANA), to_user_id=RUTH, kind="parent")


async def test_household_target_auto_confirmed_owner_only(svc, parts):
    m = MagicMock(spec=HouseholdMember)
    m.id, m.owner_id, m.deleted_at = uuid.uuid4(), DANA, None
    parts["household"].get.return_value = m
    parts["repo"].create.return_value = _rel(DANA, None)
    await svc.request(_user(DANA), to_member_id=m.id, kind="child")
    assert parts["repo"].create.call_args.kwargs["status"] == "confirmed"
    parts["notifications"].notify.assert_not_called()
    with pytest.raises(NotFoundError):  # someone else's member
        await svc.request(_user(MAYA), to_member_id=m.id, kind="child")


async def test_only_target_confirms(svc, parts):
    rel = _rel(DANA, RUTH)
    parts["repo"].get.return_value = rel
    with pytest.raises(AuthorizationError):  # sender
        await svc.confirm(rel.id, _user(DANA))
    with pytest.raises(NotFoundError):  # third party
        await svc.confirm(rel.id, _user(MAYA))
    parts["repo"].confirm.assert_not_called()
    await svc.confirm(rel.id, _user(RUTH))
    parts["repo"].confirm.assert_awaited_once()


async def test_either_side_removes_stranger_cannot(svc, parts):
    rel = _rel(DANA, RUTH)
    parts["repo"].get.return_value = rel
    await svc.remove(rel.id, _user(RUTH))
    await svc.remove(rel.id, _user(DANA))
    assert parts["repo"].delete.await_count == 2
    with pytest.raises(NotFoundError):
        await svc.remove(rel.id, _user(MAYA))
    await svc.remove(rel.id, _user(MAYA, role="admin"))
    assert parts["repo"].delete.await_count == 3


async def test_list_shows_inverse_label_to_both_sides(svc, parts):
    rel = _rel(DANA, RUTH, kind="child", status="confirmed")
    parts["repo"].involving.return_value = [rel]
    parts["profiles"].get_user.return_value = _user(RUTH)
    parts["profiles"].get_settings.return_value = None
    dana, ruth = _user(DANA, "Dana"), _user(RUTH, "Ruth", pronouns="she/her")
    parts["repo"].users_visible.return_value = {DANA: dana}
    out = await svc.list_for(RUTH, ruth)
    assert out[0].person.name == "Dana" and out[0].display == "child"
    parts["repo"].users_visible.return_value = {RUTH: ruth}
    parts["profiles"].get_user.return_value = dana
    out = await svc.list_for(DANA, dana)
    assert out[0].person.name == "Ruth" and out[0].display == "mother"


async def test_private_level_hides_list_from_others(svc, parts):
    s = MagicMock(spec=UserSettings)
    s.field_visibility, s.profile_visible_to = {"relations": "private"}, "community"
    parts["profiles"].get_user.return_value = _user(RUTH)
    parts["profiles"].get_settings.return_value = s
    assert await svc.list_for(RUTH, _user(MAYA)) == []
    parts["repo"].involving.assert_not_called()


async def test_default_level_is_community_and_pending_hidden_from_others(svc, parts):
    parts["profiles"].get_user.return_value = _user(RUTH)
    parts["profiles"].get_settings.return_value = None
    parts["repo"].involving.return_value = [_rel(DANA, RUTH, status="pending")]
    parts["repo"].users_visible.return_value = {DANA: _user(DANA)}
    assert await svc.list_for(RUTH, _user(MAYA)) == []
    assert len(await svc.list_for(RUTH, _user(RUTH))) == 1


async def test_list_blocked_viewer_gets_not_found(svc, parts):
    parts["profiles"].get_user.return_value = _user(RUTH)
    parts["profiles"].blocked_either_way.return_value = True
    with pytest.raises(NotFoundError):
        await svc.list_for(RUTH, _user(MAYA))


async def test_feature_off_blocks(svc, parts):
    parts["communities"].get.return_value.features = {"relations": False}
    with pytest.raises(AppError):
        await svc.requests(_user(RUTH))
