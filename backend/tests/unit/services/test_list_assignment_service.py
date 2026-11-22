"""@file Tests for ListAssignmentService and ListActivityService."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, AuthorizationError, NotFoundError, ValidationError
from app.models.list import List, ListItem, ListMember
from app.models.list_assignment import ListActivity, ListItemAssignment
from app.models.user import User
from app.repositories.list_activity_repo import ListActivityRepository
from app.repositories.list_assignment_repo import ListAssignmentRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_member_repo import ListMemberRepository
from app.repositories.list_repo import ListRepository
from app.services.list_activity_service import ListActivityService
from app.services.list_assignment_service import ListAssignmentService

CID = uuid.uuid4()


def _row(item, assignee, by, status):
    r = MagicMock(spec=ListItemAssignment)
    r.item_id, r.assignee_id, r.assigned_by, r.status = item.id, assignee, by, status
    return r


def _build(active=None, viewable=True):
    owner = uuid.uuid4()
    lst = MagicMock(spec=List)
    lst.id, lst.owner_id, lst.title = uuid.uuid4(), owner, "Party"
    item = MagicMock(spec=ListItem)
    item.id, item.list_id, item.values = uuid.uuid4(), lst.id, {"title": "Chairs"}
    lists = AsyncMock(spec=ListRepository)
    lists.get_by_id.return_value = lst
    lists.can_view.return_value = viewable
    items = AsyncMock(spec=ListItemRepository)
    items.lock_item_for_update.return_value = item
    assign = AsyncMock(spec=ListAssignmentRepository)
    assign.get_active.return_value = active
    members = AsyncMock(spec=ListMemberRepository)
    members.get_member.return_value = None
    arepo = AsyncMock(spec=ListActivityRepository)
    activity = ListActivityService(arepo, lists, CID)
    notify = AsyncMock()
    svc = ListAssignmentService(assign, items, lists, members, activity, CID, notify)
    return svc, lst, item, assign, members, arepo, notify, lists


def _user(active=True):
    u = MagicMock(spec=User)
    u.id, u.display_name, u.avatar_url, u.is_active = uuid.uuid4(), "Maya", None, active
    return u


async def test_take_creates_accepted_and_logs():
    svc, lst, item, assign, _m, arepo, _n, _l = _build()
    me = uuid.uuid4()
    await svc.take(lst.id, item.id, me)
    assign.add.assert_awaited_once_with(CID, lst.id, item.id, me, me, "accepted")
    args = arepo.add.await_args.args
    assert args[3] == "taken" and args[5] == "Chairs"


async def test_take_rejected_when_already_assigned():
    other = MagicMock(id=uuid.uuid4())
    svc, lst, item, *_ = _build(active=_row(other, uuid.uuid4(), None, "pending"))
    with pytest.raises(AppError) as e:
        await svc.take(lst.id, item.id, uuid.uuid4())
    assert e.value.status_code == 409


async def test_take_hidden_list_is_404():
    svc, lst, item, *_ = _build(viewable=False)
    with pytest.raises(NotFoundError):
        await svc.take(lst.id, item.id, uuid.uuid4())


async def test_assign_by_non_editor_rejected():
    svc, lst, item, assign, *_ = _build()
    with pytest.raises(AuthorizationError):
        await svc.assign(lst.id, item.id, uuid.uuid4(), uuid.uuid4())
    assign.add.assert_not_awaited()


async def test_assign_by_list_admin_member_creates_pending_and_notifies():
    svc, lst, item, assign, members, arepo, notify, _l = _build()
    editor = uuid.uuid4()
    m = MagicMock(spec=ListMember)
    m.role = "admin"
    members.get_member.return_value = m
    target = _user()
    arepo.users_by_ids.return_value = {target.id: target}
    await svc.assign(lst.id, item.id, editor, target.id)
    assign.add.assert_awaited_once_with(CID, lst.id, item.id, target.id, editor, "pending")
    assert notify.notify.await_args.args[0] == target.id
    assert notify.notify.await_args.args[1] == "list_assigned"
    assert arepo.add.await_args.args[3] == "assigned"


async def test_assign_replaces_existing_active_assignment():
    old = _row(MagicMock(id=uuid.uuid4()), uuid.uuid4(), None, "accepted")
    svc, lst, item, assign, _m, arepo, _n, _l = _build(active=old)
    target = _user()
    arepo.users_by_ids.return_value = {target.id: target}
    await svc.assign(lst.id, item.id, lst.owner_id, target.id)
    assign.remove.assert_awaited_once_with(old)
    assign.add.assert_awaited_once()


async def test_assign_to_user_who_cannot_view_is_validation_error():
    svc, lst, item, _a, _m, arepo, _n, lists = _build()
    target = _user()
    arepo.users_by_ids.return_value = {target.id: target}
    lists.can_view.side_effect = [True, False]  # actor yes, assignee no
    with pytest.raises(ValidationError) as e:
        await svc.assign(lst.id, item.id, lst.owner_id, target.id)
    assert e.value.status_code == 422


async def test_assign_unknown_user_is_validation_error():
    svc, lst, item, _a, _m, arepo, *_ = _build()
    arepo.users_by_ids.return_value = {}
    with pytest.raises(ValidationError):
        await svc.assign(lst.id, item.id, lst.owner_id, uuid.uuid4())


async def test_accept_transitions_pending_to_accepted():
    me = uuid.uuid4()
    svc, lst, item, assign, _m, arepo, notify, _l = _build()
    row = _row(item, me, lst.owner_id, "pending")
    assign.get_active.return_value = row
    await svc.respond(lst.id, item.id, me, True)
    assign.set_status.assert_awaited_once_with(row, "accepted")
    assert arepo.add.await_args.args[3] == "accepted"
    assert notify.notify.await_args.args[0] == lst.owner_id


async def test_decline_marks_declined_and_logs():
    me = uuid.uuid4()
    svc, lst, item, assign, _m, arepo, *_ = _build()
    row = _row(item, me, lst.owner_id, "pending")
    assign.get_active.return_value = row
    await svc.respond(lst.id, item.id, me, False)
    assign.set_status.assert_awaited_once_with(row, "declined")
    assert arepo.add.await_args.args[3] == "declined"


async def test_respond_by_other_user_is_404_and_non_pending_is_409():
    svc, lst, item, assign, *_ = _build()
    assign.get_active.return_value = _row(item, uuid.uuid4(), None, "pending")
    with pytest.raises(NotFoundError):
        await svc.respond(lst.id, item.id, uuid.uuid4(), True)
    me = uuid.uuid4()
    assign.get_active.return_value = _row(item, me, None, "accepted")
    with pytest.raises(AppError) as e:
        await svc.respond(lst.id, item.id, me, True)
    assert e.value.status_code == 409


async def test_release_removes_accepted_row():
    me = uuid.uuid4()
    svc, lst, item, assign, _m, arepo, *_ = _build()
    row = _row(item, me, me, "accepted")
    assign.get_active.return_value = row
    await svc.release(lst.id, item.id, me)
    assign.remove.assert_awaited_once_with(row)
    assert arepo.add.await_args.args[3] == "released"


async def test_release_pending_rejected():
    me = uuid.uuid4()
    svc, lst, item, assign, *_ = _build()
    assign.get_active.return_value = _row(item, me, None, "pending")
    with pytest.raises(AppError):
        await svc.release(lst.id, item.id, me)


async def test_unassign_requires_editor_and_active_row():
    svc, lst, item, assign, _m, arepo, *_ = _build()
    with pytest.raises(AuthorizationError):
        await svc.unassign(lst.id, item.id, uuid.uuid4())
    with pytest.raises(NotFoundError):
        await svc.unassign(lst.id, item.id, lst.owner_id)
    row = _row(item, uuid.uuid4(), None, "accepted")
    assign.get_active.return_value = row
    await svc.unassign(lst.id, item.id, lst.owner_id)
    assign.remove.assert_awaited_once_with(row)
    assert arepo.add.await_args.args[3] == "unassigned"


async def test_describe_hydrates_assignee():
    svc, lst, item, assign, _m, arepo, *_ = _build()
    u = _user()
    assign.active_for_list.return_value = {item.id: _row(item, u.id, None, "pending")}
    arepo.users_by_ids.return_value = {u.id: u}
    out = await svc.describe(lst.id, [item.id])
    assert out[item.id]["status"] == "pending"
    assert out[item.id]["assignee"]["display_name"] == "Maya"


async def test_activity_page_hydrates_and_hides_from_non_viewers():
    _s, lst, _i, _a, _m, arepo, _n, lists = _build()
    svc = ListActivityService(arepo, lists, CID)
    actor = _user()
    entry = MagicMock(spec=ListActivity)
    entry.actor_id, entry.target_user_id = actor.id, None
    arepo.list_page.return_value = ([entry], "next")
    arepo.users_by_ids.return_value = {actor.id: actor}
    rows, users, nxt = await svc.page(lst.id, actor.id, None, 10)
    assert rows == [entry] and users[actor.id] is actor and nxt == "next"
    lists.can_view.return_value = False
    with pytest.raises(NotFoundError):
        await svc.page(lst.id, actor.id, None, 10)


async def test_activity_record_delegates_to_repo():
    _s, lst, _i, _a, _m, arepo, _n, lists = _build()
    svc = ListActivityService(arepo, lists, CID)
    await svc.record(lst.id, None, "item_added", None, "X")
    arepo.add.assert_awaited_once_with(CID, lst.id, None, "item_added", None, "X", None)
