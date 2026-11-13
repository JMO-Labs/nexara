"""
@file test_list_repo_can_view.py
@brief Unit tests for ListRepository.can_view/audience_ids and completion count (nexara#385).
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.list import List
from app.repositories.list_completion_repo import ListCompletionRepository
from app.repositories.list_repo import ListRepository

UID, OWNER, LID, SGID = (uuid.uuid4() for _ in range(4))


def _session(rows: list[Any], first: Any = None, scalar: Any = 0) -> AsyncMock:
    s = AsyncMock()
    res = MagicMock()
    res.scalars.return_value.all.return_value = rows
    res.first.return_value = first
    res.scalar_one.return_value = scalar
    s.execute = AsyncMock(return_value=res)
    return s


def _list(visibility: str, owner: uuid.UUID = OWNER, subgroup: uuid.UUID | None = None) -> Any:
    lst = MagicMock(spec=List)
    lst.id, lst.owner_id, lst.visibility, lst.subgroup_id = LID, owner, visibility, subgroup
    return lst


class TestCanView:
    async def test_community_visible(self) -> None:
        assert await ListRepository(_session([])).can_view(_list("community"), UID)

    async def test_private_only_owner(self) -> None:
        repo = ListRepository(_session([]))
        assert await repo.can_view(_list("private"), OWNER)
        assert not await repo.can_view(_list("private"), UID)

    async def test_subgroup_without_id_denied(self) -> None:
        assert not await ListRepository(_session([])).can_view(_list("subgroup"), UID)

    @pytest.mark.parametrize(("expanded", "expected"), [([SGID], True), ([], False)])
    async def test_subgroup_membership(self, expanded: list[uuid.UUID], expected: bool) -> None:
        s = _session([SGID])
        with patch(
            "app.repositories.subgroup_repo.expand_with_descendants",
            AsyncMock(return_value=expanded),
        ):
            got = await ListRepository(s).can_view(_list("subgroup", subgroup=SGID), UID)
        assert got is expected

    async def test_members_owner_short_circuits(self) -> None:
        s = _session([])
        assert await ListRepository(s).can_view(_list("members", owner=UID), UID)
        s.execute.assert_not_awaited()

    async def test_members_lookup(self) -> None:
        assert await ListRepository(_session([], first=(UID,))).can_view(_list("members"), UID)
        assert not await ListRepository(_session([], first=None)).can_view(_list("members"), UID)

    async def test_unknown_visibility_denied(self) -> None:
        assert not await ListRepository(_session([])).can_view(_list("weird"), UID)


class TestAudienceIds:
    async def test_members_list(self) -> None:
        assert await ListRepository(_session([UID])).audience_ids(_list("members")) == {UID}

    async def test_subgroup_list(self) -> None:
        got = await ListRepository(_session([UID])).audience_ids(_list("subgroup", subgroup=SGID))
        assert got == {UID}

    async def test_other_visibility_empty(self) -> None:
        s = _session([UID])
        assert await ListRepository(s).audience_ids(_list("community")) == set()
        assert await ListRepository(s).audience_ids(_list("subgroup")) == set()
        s.execute.assert_not_awaited()


async def test_completion_count_for_item() -> None:
    s = _session([], scalar=3)
    assert await ListCompletionRepository(s).count_for_item(uuid.uuid4()) == 3
