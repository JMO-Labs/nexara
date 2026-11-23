"""
@file test_lists_api.py
@brief Unit tests for the lists and list_templates API routers.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.list_chores import get_chore_service
from app.core import list_dependencies as deps
from app.core.dependencies import get_current_user
from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.user import User
from app.services.chore_service import ChoreService
from app.services.list_activity_service import ListActivityService
from app.services.list_assignment_service import ListAssignmentService
from app.services.list_completion_service import ListCompletionService
from app.services.list_items_service import ListItemService
from app.services.list_service import ListService
from app.services.list_signup_service import ListSignupService
from app.services.list_template_service import ListTemplateService

NOW = datetime.now(UTC)
LID = uuid.uuid4()
IID = uuid.uuid4()
COMMUNITY = uuid.uuid4()


def _list(**kw):
    base = dict(
        id=LID, title="T", description=None, visibility="community", owner_id=uuid.uuid4(),
        community_id=COMMUNITY, template_id=None, subgroup_id=None, status="active",
        expires_at=None, color=None, item_count=0, completed_count=0, signup_count=0,
        created_at=NOW, updated_at=NOW, field_schema=[],
    )  # fmt: skip
    base.update(kw)
    return SimpleNamespace(**base)


def _item():
    return SimpleNamespace(
        id=IID, position=0, values={}, due_at=None, completed=False, completed_by=None,
        completed_at=None, lat=None, lon=None, signup_quantity_needed=None,
    )  # fmt: skip


def _tpl():
    return SimpleNamespace(
        id=uuid.uuid4(), name="N", category=None, icon=None, color=None, cover_media_id=None,
        is_shared=False, created_at=NOW, updated_at=NOW, fields=[], items=[],
    )  # fmt: skip


@pytest.fixture
def user() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.role = "member"
    return u


@pytest.fixture
def mocks() -> dict:
    return {
        "list": AsyncMock(spec=ListService),
        "item": AsyncMock(spec=ListItemService),
        "comp": AsyncMock(spec=ListCompletionService),
        "signup": AsyncMock(spec=ListSignupService),
        "tpl": AsyncMock(spec=ListTemplateService),
        "assign": AsyncMock(spec=ListAssignmentService),
        "activity": AsyncMock(spec=ListActivityService),
        "chores": AsyncMock(spec=ChoreService, enabled=MagicMock(return_value=False)),
    }


@pytest.fixture
async def client(test_app, user, mocks):
    o = test_app.dependency_overrides
    o[get_current_user] = lambda: user
    o[deps.get_community_id] = lambda: COMMUNITY
    o[deps.get_list_service] = lambda: mocks["list"]
    o[deps.get_list_item_service] = lambda: mocks["item"]
    o[deps.get_list_completion_service] = lambda: mocks["comp"]
    o[deps.get_list_signup_service] = lambda: mocks["signup"]
    o[deps.get_list_template_service] = lambda: mocks["tpl"]
    mocks["assign"].describe.return_value = {}
    o[deps.get_list_assignment_service] = lambda: mocks["assign"]
    o[deps.get_list_activity_service] = lambda: mocks["activity"]
    o[get_chore_service] = lambda: mocks["chores"]
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        yield c
    o.clear()


async def test_create_list_201(client, mocks) -> None:
    mocks["list"].create.return_value = _list()
    r = await client.post("/api/v1/lists", json={"title": "T"})
    assert r.status_code == 201
    assert r.json()["id"] == str(LID)


async def test_list_lists_returns_cursor(client, mocks, user) -> None:
    mocks["list"].list_visible.return_value = ([_list()], "abc")
    r = await client.get("/api/v1/lists?limit=5&cursor=xyz")
    assert r.status_code == 200
    assert r.json()["pagination"] == {"cursor": "abc", "has_more": True}
    mocks["list"].list_visible.assert_awaited_once_with(user.id, "xyz", 5)


async def test_get_list_not_found_envelope(client, mocks) -> None:
    mocks["list"].get_by_id.side_effect = NotFoundError("List not found")
    r = await client.get(f"/api/v1/lists/{LID}")
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "NOT_FOUND"
    assert err["message"] == "List not found"


async def test_update_list_forbidden_403(client, mocks) -> None:
    mocks["list"].update.side_effect = AuthorizationError("no")
    r = await client.put(f"/api/v1/lists/{LID}", json={"title": "x"})
    assert r.status_code == 403
    err = r.json()["error"]
    assert err["code"] == "AUTHORIZATION_ERROR"
    assert err["message"] == "no"


async def test_update_list_passes_admin_flag(client, mocks, user) -> None:
    user.role = "admin"
    mocks["list"].update.return_value = _list()
    r = await client.put(f"/api/v1/lists/{LID}", json={"title": "x"})
    assert r.status_code == 200
    mocks["list"].update.assert_awaited_once_with(LID, user.id, {"title": "x"}, True)


async def test_archive_list_calls_service(client, mocks, user) -> None:
    user.role = "admin"
    mocks["list"].archive.return_value = _list(status="archived")
    r = await client.post(f"/api/v1/lists/{LID}/archive")
    assert r.status_code == 200
    assert r.json()["status"] == "archived"
    mocks["list"].archive.assert_awaited_once_with(LID, user.id, True)


async def test_delete_list_204(client, mocks) -> None:
    r = await client.delete(f"/api/v1/lists/{LID}")
    assert r.status_code == 204
    mocks["list"].delete.assert_awaited_once()


async def test_item_create_201(client, mocks, user) -> None:
    mocks["item"].create.return_value = _item()
    r = await client.post(f"/api/v1/lists/{LID}/items", json={"position": 1, "values": {"a": 1}})
    assert r.status_code == 201
    mocks["item"].create.assert_awaited_once_with(COMMUNITY, LID, user.id, {"a": 1}, 1)


async def test_item_list(client, mocks) -> None:
    mocks["item"].list_items.return_value = ([_item()], None)
    r = await client.get(f"/api/v1/lists/{LID}/items")
    assert r.status_code == 200
    assert r.json()["pagination"]["has_more"] is False


async def test_item_update_and_delete(client, mocks) -> None:
    mocks["item"].update.return_value = _item()
    r = await client.put(f"/api/v1/lists/{LID}/items/{IID}", json={"values": {"a": 2}})
    assert r.status_code == 200
    r = await client.delete(f"/api/v1/lists/{LID}/items/{IID}")
    assert r.status_code == 204


async def test_complete_and_uncomplete(client, mocks, user) -> None:
    mocks["comp"].complete_item.return_value = _item()
    mocks["comp"].uncomplete_item.return_value = _item()
    r = await client.post(f"/api/v1/lists/{LID}/items/{IID}/complete")
    assert r.status_code == 200
    mocks["comp"].complete_item.assert_awaited_once_with(IID, user.id, None)
    r = await client.post(f"/api/v1/lists/{LID}/items/{IID}/uncomplete")
    assert r.status_code == 200


async def test_members_add_list_remove(client, mocks) -> None:
    mid = uuid.uuid4()
    member = MagicMock(list_id=LID, user_id=mid, role="viewer", share_personal=False, added_at=NOW)
    mocks["list"].add_member.return_value = member
    r = await client.post(f"/api/v1/lists/{LID}/members", json={"user_id": str(mid)})
    assert r.status_code == 201
    r = await client.delete(f"/api/v1/lists/{LID}/members/{mid}")
    assert r.status_code == 204


async def test_signup_claim_and_release(client, mocks) -> None:
    mocks["signup"].claim_signup.return_value = MagicMock(
        item_id=IID, user_id=uuid.uuid4(), quantity=2, note=None, claimed_at=NOW
    )
    r = await client.post(f"/api/v1/lists/{LID}/items/{IID}/signups", json={"quantity": 2})
    assert r.status_code == 201
    r = await client.delete(f"/api/v1/lists/{LID}/items/{IID}/signups")
    assert r.status_code == 204
    mocks["signup"].release_signup.assert_awaited_once()


async def test_template_crud_and_clone(client, mocks) -> None:
    tid = uuid.uuid4()
    mocks["tpl"].create.return_value = _tpl()
    mocks["tpl"].list_for_community.return_value = ([_tpl()], None)
    mocks["tpl"].get_by_id.return_value = _tpl()
    mocks["tpl"].update.return_value = _tpl()
    mocks["tpl"].clone_template_to_list.return_value = _list()
    assert (await client.post("/api/v1/list_templates", json={"name": "N"})).status_code == 201
    assert (await client.get("/api/v1/list_templates")).status_code == 200
    assert (await client.get(f"/api/v1/list_templates/{tid}")).status_code == 200
    assert (
        await client.put(f"/api/v1/list_templates/{tid}", json={"name": "M"})
    ).status_code == 200
    assert (await client.delete(f"/api/v1/list_templates/{tid}")).status_code == 204
    r = await client.post(f"/api/v1/list_templates/{tid}/clone", json={})
    assert r.status_code == 201


async def test_members_get_lists_members(client, mocks, user) -> None:
    mid = uuid.uuid4()
    member = MagicMock(list_id=LID, user_id=mid, role="viewer", share_personal=False, added_at=NOW)
    mocks["list"].list_members.return_value = [member]
    r = await client.get(f"/api/v1/lists/{LID}/members")
    assert r.status_code == 200
    assert r.json()[0]["user_id"] == str(mid)
    mocks["list"].list_members.assert_awaited_once_with(LID, user.id)


async def test_members_get_hidden_list_404(client, mocks) -> None:
    mocks["list"].list_members.side_effect = NotFoundError("List not found")
    r = await client.get(f"/api/v1/lists/{LID}/members")
    assert r.status_code == 404


async def test_signups_hidden_list_404(client, mocks) -> None:
    mocks["list"].get_by_id.side_effect = NotFoundError("List not found")
    r = await client.get(f"/api/v1/lists/{LID}/items/{IID}/signups")
    assert r.status_code == 404
    r = await client.post(f"/api/v1/lists/{LID}/items/{IID}/signups", json={"quantity": 1})
    assert r.status_code == 404
    r = await client.delete(f"/api/v1/lists/{LID}/items/{IID}/signups")
    assert r.status_code == 404
    mocks["signup"].get_signups_for_item.assert_not_awaited()
    mocks["signup"].claim_signup.assert_not_awaited()
    mocks["signup"].release_signup.assert_not_awaited()


@pytest.mark.parametrize(
    ("method", "suffix", "body", "svc", "fn"),
    [
        ("put", "", {"values": {}}, "item", "update"),
        ("delete", "", None, "item", "delete"),
        ("post", "/complete", None, "comp", "complete_item"),
        ("post", "/uncomplete", None, "comp", "uncomplete_item"),
        ("get", "/signups", None, "signup", "get_signups_for_item"),
    ],
)
async def test_item_routes_reject_list_mismatch(
    client, mocks, method, suffix, body, svc, fn
) -> None:
    mocks["item"].ensure_in_list.side_effect = NotFoundError("Item not found")
    r = await client.request(method, f"/api/v1/lists/{LID}/items/{IID}{suffix}", json=body)
    assert r.status_code == 404
    getattr(mocks[svc], fn).assert_not_awaited()


async def test_get_signups_returns_claims(client, mocks) -> None:
    mocks["signup"].get_signups_for_item.return_value = []
    r = await client.get(f"/api/v1/lists/{LID}/items/{IID}/signups")
    assert r.status_code == 200
    assert r.json() == []
    mocks["signup"].get_signups_for_item.assert_awaited_once_with(IID)


async def test_take_item_returns_assignee(client, mocks) -> None:
    uid = uuid.uuid4()
    mocks["assign"].take.return_value = _item()
    mocks["assign"].describe.return_value = {
        IID: {
            "assignee": {"id": uid, "display_name": "Maya", "avatar_url": None},
            "status": "accepted",
        }
    }
    r = await client.post(f"/api/v1/lists/{LID}/items/{IID}/take")
    assert r.status_code == 200
    assert r.json()["assignee"]["display_name"] == "Maya"
    assert r.json()["assignment_status"] == "accepted"


async def test_assign_decline_release_unassign_routes(client, mocks) -> None:
    for name in ("assign", "respond", "release", "unassign"):
        getattr(mocks["assign"], name).return_value = _item()
    base = f"/api/v1/lists/{LID}/items/{IID}"
    assert (
        await client.post(f"{base}/assign", json={"user_id": str(uuid.uuid4())})
    ).status_code == 200
    assert (await client.post(f"{base}/assignment/accept")).status_code == 200
    assert (await client.post(f"{base}/assignment/decline")).status_code == 200
    assert mocks["assign"].respond.await_args_list[1].args[3] is False
    assert (await client.post(f"{base}/release")).status_code == 200
    assert (await client.delete(f"{base}/assignment")).status_code == 200


async def test_assign_forbidden_maps_to_403(client, mocks) -> None:
    mocks["assign"].assign.side_effect = AuthorizationError("no")
    r = await client.post(
        f"/api/v1/lists/{LID}/items/{IID}/assign", json={"user_id": str(uuid.uuid4())}
    )
    assert r.status_code == 403


async def test_activity_feed_page(client, mocks) -> None:
    uid = uuid.uuid4()
    entry = SimpleNamespace(
        id=uuid.uuid4(), action="taken", actor_id=uid, item_id=IID, item_title="Chairs",
        target_user_id=None, created_at=NOW,
    )  # fmt: skip
    actor = SimpleNamespace(id=uid, display_name="Maya", avatar_url=None)
    mocks["activity"].page.return_value = ([entry], {uid: actor}, "cur")
    r = await client.get(f"/api/v1/lists/{LID}/activity?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["activity"][0]["actor"]["display_name"] == "Maya"
    assert body["pagination"] == {"cursor": "cur", "has_more": True}


async def test_set_chore_route(client, mocks) -> None:
    item = SimpleNamespace(
        id=uuid.uuid4(), position=0, values={}, due_at=None, completed=False,
        completed_by=None, completed_at=None, lat=None, lon=None,
        signup_quantity_needed=None, recipe_id=None, repeat="weekly",
        rotation=[], rotation_index=0, next_due_at=None,
    )  # fmt: skip
    mocks["chores"].set_schedule.return_value = item
    mocks["chores"].next_assignees.return_value = {}
    r = await client.put(
        f"/api/v1/lists/{LID}/items/{item.id}/chore", json={"repeat": "weekly", "rotation": []}
    )
    assert r.status_code == 200 and r.json()["repeat"] == "weekly"
    r = await client.put(f"/api/v1/lists/{LID}/items/{item.id}/chore", json={"repeat": "hourly"})
    assert r.status_code == 422
