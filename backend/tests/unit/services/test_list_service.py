"""
@file test_list_service.py
@brief Unit tests for ListService visibility, auth and CRUD.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.models.list import List, ListMember
from app.repositories.list_member_repo import ListMemberRepository
from app.repositories.list_repo import ListRepository
from app.services.list_service import ListService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _list(visibility="community", owner=None, subgroup_id=None) -> MagicMock:
    obj = MagicMock(spec=List)
    obj.id = uuid.uuid4()
    obj.community_id = CID
    obj.owner_id = owner or uuid.uuid4()
    obj.visibility = visibility
    obj.subgroup_id = subgroup_id
    obj.status = "active"
    return obj


def _svc(session=None):
    repo = AsyncMock(spec=ListRepository)
    members = AsyncMock(spec=ListMemberRepository)
    repo.update.side_effect = lambda e, d: e
    svc = ListService(repo, members, MagicMock(), CID, session or AsyncMock())
    svc._subgroup_ids = AsyncMock(return_value=[])
    return svc, repo, members


class TestCanView:
    async def test_community(self):
        svc, _, _ = _svc()
        assert await svc._can_view(_list(), uuid.uuid4())

    async def test_private(self):
        svc, _, _ = _svc()
        owner = uuid.uuid4()
        assert await svc._can_view(_list("private", owner), owner)
        assert not await svc._can_view(_list("private", owner), uuid.uuid4())

    async def test_subgroup(self):
        svc, _, _ = _svc()
        sg = uuid.uuid4()
        svc._subgroup_ids.return_value = [sg]
        assert await svc._can_view(_list("subgroup", subgroup_id=sg), uuid.uuid4())
        assert not await svc._can_view(_list("subgroup", subgroup_id=uuid.uuid4()), uuid.uuid4())
        assert not await svc._can_view(_list("subgroup"), uuid.uuid4())

    async def test_members(self):
        svc, _, members = _svc()
        lst, uid = _list("members"), uuid.uuid4()
        members.get_member.return_value = MagicMock(spec=ListMember)
        assert await svc._can_view(lst, uid)
        members.get_member.return_value = None
        assert not await svc._can_view(lst, uid)
        assert await svc._can_view(lst, lst.owner_id)


class TestCanEdit:
    async def test_owner_admin_other(self):
        svc, _, members = _svc()
        lst = _list()
        members.get_member.return_value = None
        assert await svc._can_edit(lst, lst.owner_id)
        assert await svc._can_edit(lst, uuid.uuid4(), is_admin=True)
        assert not await svc._can_edit(lst, uuid.uuid4())
        members.get_member.return_value = MagicMock(spec=ListMember, role="admin")
        assert await svc._can_edit(lst, uuid.uuid4())


class TestCrud:
    async def test_create_initializes(self):
        svc, repo, _ = _svc()
        repo.create.side_effect = lambda e: e
        out = await svc.create(uuid.uuid4(), title="T", visibility="community")
        assert (out.item_count, out.completed_count, out.signup_count) == (0, 0, 0)
        assert out.field_schema == []
        assert out.community_id == CID

    async def test_create_subgroup_requires_id(self):
        svc, _, _ = _svc()
        with pytest.raises(AppError):
            await svc.create(uuid.uuid4(), title="T", visibility="subgroup")

    async def test_get_hidden_raises_not_found(self):
        svc, repo, _ = _svc()
        repo.get_by_id.return_value = _list("private")
        with pytest.raises(NotFoundError):
            await svc.get_by_id(uuid.uuid4(), uuid.uuid4())
        repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await svc.get_by_id(uuid.uuid4(), uuid.uuid4())

    async def test_list_visible_delegates(self):
        svc, repo, _ = _svc()
        repo.list_visible.return_value = ([], None)
        uid = uuid.uuid4()
        await svc.list_visible(uid, cursor="c", limit=5)
        kw = repo.list_visible.call_args.kwargs
        assert kw["cursor"] == "c" and kw["limit"] == 5 and kw["subgroup_ids"] == []

    async def test_update_forbidden(self):
        svc, repo, members = _svc()
        members.get_member.return_value = None
        repo.get_by_id.return_value = _list()
        with pytest.raises(AuthorizationError):
            await svc.update(uuid.uuid4(), uuid.uuid4(), {"title": "x"})

    async def test_update_writable_only(self):
        svc, repo, _ = _svc()
        lst = _list()
        repo.get_by_id.return_value = lst
        await svc.update(lst.id, lst.owner_id, {"title": "x", "owner_id": uuid.uuid4()})
        repo.update.assert_awaited_once_with(lst, {"title": "x"})

    async def test_delete_owner_only(self):
        svc, repo, _ = _svc()
        lst = _list()
        repo.get_by_id.return_value = lst
        with pytest.raises(AuthorizationError):
            await svc.delete(lst.id, uuid.uuid4(), is_admin=True)
        await svc.delete(lst.id, lst.owner_id)
        repo.soft_delete.assert_awaited_once_with(lst)

    async def test_archive(self):
        svc, repo, _ = _svc()
        lst = _list()
        repo.get_by_id.return_value = lst
        await svc.archive(lst.id, lst.owner_id)
        repo.update.assert_awaited_once_with(lst, {"status": "archived"})


class TestMembers:
    async def test_add_requires_members_visibility(self):
        svc, repo, members = _svc()
        lst = _list("community")
        repo.get_by_id.return_value = lst
        with pytest.raises(AppError):
            await svc.add_member(lst.id, lst.owner_id, uuid.uuid4())

    async def test_add_member(self):
        svc, repo, members = _svc()
        lst = _list("members")
        repo.get_by_id.return_value = lst
        members.get_member.return_value = None
        uid = uuid.uuid4()
        await svc.add_member(lst.id, lst.owner_id, uid, role="editor")
        members.add_member.assert_awaited_once_with(lst.id, uid, "editor")

    async def test_add_member_forbidden(self):
        svc, repo, members = _svc()
        lst = _list("members")
        repo.get_by_id.return_value = lst
        members.get_member.return_value = MagicMock(spec=ListMember, role="viewer")
        with pytest.raises(AuthorizationError):
            await svc.add_member(lst.id, uuid.uuid4(), uuid.uuid4())

    async def test_add_duplicate_conflicts(self):
        svc, repo, members = _svc()
        lst = _list("members")
        repo.get_by_id.return_value = lst
        members.get_member.return_value = MagicMock(spec=ListMember)
        with pytest.raises(AppError):
            await svc.add_member(lst.id, lst.owner_id, uuid.uuid4())

    async def test_remove_missing_not_found(self):
        svc, repo, members = _svc()
        lst = _list("members")
        repo.get_by_id.return_value = lst
        members.get_member.return_value = None
        with pytest.raises(NotFoundError):
            await svc.remove_member(lst.id, lst.owner_id, uuid.uuid4())

    async def test_remove_member(self):
        svc, repo, members = _svc()
        lst = _list("members")
        repo.get_by_id.return_value = lst
        m = MagicMock(spec=ListMember)
        members.get_member.return_value = m
        await svc.remove_member(lst.id, lst.owner_id, uuid.uuid4())
        members.remove_member.assert_awaited_once_with(m)

    async def test_share_self_only(self):
        svc, repo, members = _svc()
        lst = _list("members")
        repo.get_by_id.return_value = lst
        m = MagicMock(spec=ListMember)
        members.get_member.return_value = m
        uid = uuid.uuid4()
        await svc.update_member_share(lst.id, uid, True)
        members.update_member.assert_awaited_once_with(m, {"share_personal": True})
