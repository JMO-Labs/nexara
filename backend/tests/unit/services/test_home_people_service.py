"""
@file test_home_people_service.py
@brief Unit tests for HomePeopleService.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

from app.models.user import User
from app.repositories.home_people_repo import HomePeopleRepository, PersonRow
from app.services.home_people_service import HomePeopleService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TODAY = date(2026, 11, 19)


def _row(
    name: str,
    *,
    birthday: date | None = None,
    last_seen: datetime | None = None,
    show_online: bool = True,
    show_last_seen: bool = True,
    show_birthday_to: str = "community",
    groups: list[tuple[uuid.UUID, str, str | None, int]] | None = None,
) -> PersonRow:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.username = name.lower()
    u.display_name = name
    u.avatar_url = None
    u.birthday = birthday
    u.last_seen_at = last_seen
    return PersonRow(
        user=u,
        show_online_status=show_online,
        show_last_seen=show_last_seen,
        show_birthday_to=show_birthday_to,
        shared_groups=groups or [],
    )


def _svc(rows: list[PersonRow], online: list[PersonRow] | None = None, today: date = TODAY):
    repo = AsyncMock(spec=HomePeopleRepository)
    repo.candidates.return_value = rows
    repo.shared_event_counts.return_value = {}
    repo.favorites.return_value = []
    repo.rows_for.return_value = []

    async def online_fn() -> list[str]:
        return [str(r.user.id) for r in (online or [])]

    svc = HomePeopleService(repo, COMMUNITY_ID, online_fn=online_fn, today_fn=lambda: today)
    return svc, repo


def _viewer() -> MagicMock:
    v = MagicMock(spec=User)
    v.id = uuid.uuid4()
    return v


async def test_orders_online_then_birthday_then_recent():
    ruth = _row("Ruth")
    leo = _row("Leo", birthday=date(1990, 11, 21))
    kim = _row("Kim", last_seen=datetime(2026, 11, 18, tzinfo=UTC))
    old = _row("Old", last_seen=datetime(2026, 11, 1, tzinfo=UTC))
    svc, _ = _svc([old, kim, leo, ruth], online=[ruth])
    r = await svc.list(_viewer(), 10)
    assert [p.display_name for p in r.items] == ["Ruth", "Leo", "Kim", "Old"]


async def test_limit_applies_after_sorting():
    ruth = _row("Ruth")
    kim = _row("Kim")
    svc, _ = _svc([kim, ruth], online=[ruth])
    r = await svc.list(_viewer(), 1)
    assert [p.display_name for p in r.items] == ["Ruth"]


async def test_hides_online_when_flag_off():
    ruth = _row("Ruth", show_online=False)
    svc, _ = _svc([ruth], online=[ruth])
    r = await svc.list(_viewer(), 10)
    assert r.items[0].online is False


async def test_hides_last_seen_when_flag_off():
    kim = _row("Kim", last_seen=datetime(2026, 11, 18, tzinfo=UTC), show_last_seen=False)
    svc, _ = _svc([kim])
    r = await svc.list(_viewer(), 10)
    assert r.items[0].last_seen_at is None


async def test_hides_birthday_unless_community():
    leo = _row("Leo", birthday=date(1990, 11, 20), show_birthday_to="nobody")
    svc, _ = _svc([leo])
    r = await svc.list(_viewer(), 10)
    assert r.items[0].birthday_in_days is None


async def test_birthday_today_and_out_of_window():
    a = _row("A", birthday=date(1990, 11, 19))
    b = _row("B", birthday=date(1990, 12, 4))
    svc, _ = _svc([a, b])
    r = await svc.list(_viewer(), 10)
    by = {p.display_name: p.birthday_in_days for p in r.items}
    assert by == {"A": 0, "B": None}


async def test_birthday_wraps_year():
    leo = _row("Leo", birthday=date(1990, 1, 2))
    svc, _ = _svc([leo], today=date(2026, 12, 30))
    r = await svc.list(_viewer(), 10)
    assert r.items[0].birthday_in_days == 3


async def test_feb_29_birthday_treated_as_feb_28_in_non_leap_year():
    leo = _row("Leo", birthday=date(1992, 2, 29))
    svc, _ = _svc([leo], today=date(2027, 2, 26))
    r = await svc.list(_viewer(), 10)
    assert r.items[0].birthday_in_days == 2


async def test_primary_group_is_smallest_shared():
    small, big = uuid.uuid4(), uuid.uuid4()
    p = _row("Ana", groups=[(big, "Big", None, 20), (small, "Small", "#123456", 3)])
    svc, _ = _svc([p])
    r = await svc.list(_viewer(), 10)
    assert r.items[0].primary_group_id == small
    assert {g.id for g in r.items[0].shared_groups} == {small, big}


async def test_primary_group_tie_breaks_by_name():
    a, b = uuid.uuid4(), uuid.uuid4()
    p = _row("Ana", groups=[(b, "Zed", None, 3), (a, "Alpha", None, 3)])
    svc, _ = _svc([p])
    r = await svc.list(_viewer(), 10)
    assert r.items[0].primary_group_id == a


async def test_shared_events_count_attached():
    p = _row("Ana")
    svc, repo = _svc([p])
    repo.shared_event_counts.return_value = {p.user.id: 2}
    r = await svc.list(_viewer(), 10)
    assert r.items[0].shared_events_30d == 2


async def test_favorites_first_in_pin_order_and_fetched_if_missing():
    ruth, kim = _row("Ruth"), _row("Kim")
    far = _row("Far")
    svc, repo = _svc([ruth, kim], online=[ruth])
    repo.favorites.return_value = [far.user.id, kim.user.id]
    repo.rows_for.return_value = [far]
    r = await svc.list(_viewer(), 10)
    assert [(p.display_name, p.favorite) for p in r.items] == [
        ("Far", True),
        ("Kim", True),
        ("Ruth", False),
    ]
    repo.rows_for.assert_awaited_once()


async def test_set_favorite_pins_unpins_and_rejects_unknown():
    import pytest

    from app.core.exceptions import AppError, NotFoundError

    a = _row("A")
    svc, repo = _svc([])
    repo.rows_for.return_value = [a]
    assert await svc.set_favorite(_viewer(), a.user.id, True) == [a.user.id]
    repo.favorites.return_value = [a.user.id]
    assert await svc.set_favorite(_viewer(), a.user.id, False) == []
    repo.rows_for.return_value = []
    with pytest.raises(NotFoundError):
        await svc.set_favorite(_viewer(), uuid.uuid4(), True)
    repo.rows_for.return_value = [a]
    repo.favorites.return_value = [uuid.uuid4() for _ in range(24)]
    with pytest.raises(AppError):
        await svc.set_favorite(_viewer(), a.user.id, True)
