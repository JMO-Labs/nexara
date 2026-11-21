"""
@file test_people_directory_service.py
@brief Unit tests for PeopleDirectoryService.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ValidationError
from app.models.user import User
from app.repositories.home_people_repo import PersonRow
from app.repositories.people_directory_repo import PeopleDirectoryRepository
from app.services.people_directory_service import PeopleDirectoryService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _row(name: str, *, show_online=True, show_last_seen=True, groups=None) -> PersonRow:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.username = name.lower()
    u.display_name = name
    u.avatar_url = None
    u.last_seen_at = datetime(2026, 11, 18, tzinfo=UTC)
    return PersonRow(
        user=u,
        show_online_status=show_online,
        show_last_seen=show_last_seen,
        shared_groups=groups or [],
    )


def _viewer(role: str = "member") -> MagicMock:
    v = MagicMock(spec=User)
    v.id = uuid.uuid4()
    v.role = role
    return v


def _svc(rows, online=()):
    repo = AsyncMock(spec=PeopleDirectoryRepository)
    repo.page.return_value = rows

    async def online_fn() -> list[str]:
        return [str(r.user.id) for r in online]

    return PeopleDirectoryService(repo, CID, online_fn=online_fn), repo


async def test_applies_privacy_flags_and_online():
    shy = _row("Shy", show_online=False, show_last_seen=False)
    ruth = _row("Ruth")
    svc, _ = _svc([ruth, shy], online=[ruth, shy])
    r = await svc.list(_viewer(), q=None, filter="all", limit=10, cursor=None)
    by = {p.display_name: p for p in r.items}
    assert by["Ruth"].online is True and by["Ruth"].last_seen_at is not None
    assert by["Shy"].online is False and by["Shy"].last_seen_at is None


async def test_next_cursor_when_more_rows_than_limit():
    rows = [_row("A"), _row("B"), _row("C")]
    svc, repo = _svc(rows)
    r = await svc.list(_viewer(), q=None, filter="all", limit=2, cursor=None)
    assert [p.display_name for p in r.items] == ["A", "B"]
    assert r.next_cursor == "2"
    assert repo.page.call_args.kwargs["limit"] == 3


async def test_no_cursor_on_last_page_and_offset_passed():
    svc, repo = _svc([_row("A")])
    r = await svc.list(_viewer(), q=None, filter="all", limit=2, cursor="4")
    assert r.next_cursor is None
    assert repo.page.call_args.kwargs["offset"] == 4


async def test_filters_map_to_repo_args_and_admin_flag():
    ruth = _row("Ruth")
    svc, repo = _svc([], online=[ruth])
    await svc.list(_viewer("admin"), q=" ru ", filter="online", limit=5, cursor=None)
    kw = repo.page.call_args.kwargs
    assert kw["online_ids"] == [str(ruth.user.id)]
    assert kw["viewer_is_admin"] is True and kw["q"] == "ru"
    await svc.list(_viewer(), q=None, filter="groups", limit=5, cursor=None)
    kw = repo.page.call_args.kwargs
    assert kw["groups_only"] is True and kw["online_ids"] is None


async def test_primary_group_is_smallest_group():
    big, small = uuid.uuid4(), uuid.uuid4()
    p = _row("A", groups=[(big, "Big", None, 9), (small, "Small", "#fff", 2)])
    svc, _ = _svc([p])
    r = await svc.list(_viewer(), q=None, filter="all", limit=5, cursor=None)
    assert r.items[0].primary_group_id == small
    assert len(r.items[0].shared_groups) == 2


async def test_bad_cursor_raises_validation_error():
    svc, _ = _svc([])
    with pytest.raises(ValidationError):
        await svc.list(_viewer(), q=None, filter="all", limit=5, cursor="abc")
