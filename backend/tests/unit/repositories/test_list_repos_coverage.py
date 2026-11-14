"""
@file test_list_repos_coverage.py
@brief Extra unit tests covering remaining list repository lines (nexara#361).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.dialects import postgresql

from app.models.list import ListItem, ListItemCompletion, ListItemSignup, ListMember
from app.models.list_template import ListTemplate
from app.repositories.list_completion_repo import ListCompletionRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_member_repo import ListMemberRepository
from app.repositories.list_repo import ListRepository
from app.repositories.list_signup_repo import ListSignupRepository
from app.repositories.list_template_repo import ListTemplateRepository

CID, UID, LID, IID = (uuid.uuid4() for _ in range(4))


def _session(rows: list[Any], rowcount: int = 1) -> AsyncMock:
    s = AsyncMock()
    s.add = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    result.scalar_one_or_none.return_value = rows[0] if rows else None
    result.rowcount = rowcount
    s.execute = AsyncMock(return_value=result)
    return s


def _sql(s: AsyncMock) -> str:
    return str(s.execute.call_args_list[-1].args[0].compile(dialect=postgresql.dialect()))


def _rows(model: type, n: int) -> list[Any]:
    out = []
    for _ in range(n):
        r = MagicMock(spec=model)
        r.id, r.created_at, r.position = uuid.uuid4(), datetime.now(UTC), 1
        out.append(r)
    return out


async def test_completion_get_create_delete() -> None:
    s = _session([])
    repo = ListCompletionRepository(s)
    assert await repo.get_completion(IID, UID) is None
    assert "list_item_completion.user_id" in _sql(s)
    comp = await repo.create_completion(IID, UID)
    assert isinstance(comp, ListItemCompletion) and comp.item_id == IID
    assert await repo.delete_completion(IID, UID) is True
    assert "DELETE FROM list_item_completion" in _sql(s)
    miss = ListCompletionRepository(_session([], rowcount=0))
    assert await miss.delete_completion(IID, UID) is False


async def test_item_keyset_next_cursor() -> None:
    s = _session(_rows(ListItem, 3))
    page, nxt = await ListItemRepository(s).list_items_keyset(LID, limit=2)
    assert len(page) == 2 and nxt is not None


async def test_member_repo_all_methods() -> None:
    m = MagicMock(spec=ListMember)
    s = _session([m])
    repo = ListMemberRepository(s)
    assert await repo.get_member(LID, UID) is m
    assert "list_member.user_id" in _sql(s)
    assert await repo.list_members(LID) == [m]
    assert "ORDER BY list_member.added_at ASC" in _sql(s)
    added = await repo.add_member(LID, UID, "editor")
    assert added.role == "editor"
    assert await repo.update_member(m, {"role": "editor"}) is m
    assert m.role == "editor"
    real = ListMember(list_id=LID, user_id=UID, role="viewer")
    await repo.remove_member(real)
    s.delete.assert_awaited_once_with(real)


async def test_list_visible_resolves_member_ids_when_none() -> None:
    s = _session([])
    await ListRepository(s).list_visible(CID, UID)
    assert s.execute.await_count == 2
    first = str(s.execute.call_args_list[0].args[0].compile(dialect=postgresql.dialect()))
    assert "list_member" in first


async def test_list_visible_membership_branch_with_ids() -> None:
    s = _session([])
    await ListRepository(s).list_visible(CID, UID, [], [LID])
    assert "list.id IN" in _sql(s)


async def test_increment_counters_empty_delta_noop() -> None:
    s = _session([])
    await ListRepository(s).increment_counters(LID, {})
    s.execute.assert_not_awaited()


async def test_signup_repo_methods() -> None:
    s = _session([])
    repo = ListSignupRepository(s)
    claim = await repo.create_claim(IID, UID, quantity=2, note="hi")
    assert isinstance(claim, ListItemSignup) and claim.quantity == 2
    assert await repo.delete_claim(IID, UID) is True
    assert "DELETE FROM list_item_signup" in _sql(s)
    miss = ListSignupRepository(_session([], rowcount=0))
    assert await miss.delete_claim(IID, UID) is False
    await repo.list_for_item(IID)
    assert "ORDER BY list_item_signup.claimed_at ASC" in _sql(s)


async def test_template_cursor_and_next_page() -> None:
    s = _session(_rows(ListTemplate, 3))
    repo = ListTemplateRepository(s)
    page, nxt = await repo.list_for_community(CID, UID, limit=2)
    assert len(page) == 2 and nxt is not None
    await repo.list_for_community(CID, UID, cursor=nxt)
    assert "(list_template.created_at, list_template.id) <" in _sql(s)
