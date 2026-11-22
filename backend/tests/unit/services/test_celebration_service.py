"""@file test_celebration_service.py @brief Calendar birthdays and gotcha days."""

from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ValidationError
from app.services.celebration_service import CelebrationService, occurrences

CID = uuid.uuid4()


def test_occurrences_span_years_and_leap_day():
    assert occurrences(date(1990, 1, 3), date(2026, 12, 20), date(2027, 1, 10)) == [
        date(2027, 1, 3)
    ]
    assert occurrences(date(2000, 2, 29), date(2027, 2, 1), date(2028, 3, 1)) == [
        date(2027, 2, 28),
        date(2028, 2, 29),
    ]
    assert occurrences(date(1990, 6, 1), date(2026, 7, 1), date(2026, 8, 1)) == []


async def test_people_and_pets_in_range():
    repo, house = AsyncMock(), AsyncMock()
    uid = uuid.uuid4()
    repo.user_birthdays.return_value = [(uid, "ruth", "Ruth", date(1950, 12, 2))]
    pet = SimpleNamespace(
        id=uuid.uuid4(),
        kind="pet",
        name="Biscuit",
        birthday=date(2021, 12, 12),
        gotcha_day=date(2021, 12, 1),
    )
    kid = SimpleNamespace(
        id=uuid.uuid4(), kind="person", name="James", birthday=None, gotcha_day=date(2020, 12, 5)
    )
    house.visible.return_value = [pet, kid]
    svc = CelebrationService(repo, house, CID)
    viewer = SimpleNamespace(id=uuid.uuid4())
    out = await svc.in_range(viewer, date(2026, 12, 1), date(2026, 12, 31))
    assert [(c.date.day, c.name, c.occasion, c.is_pet) for c in out] == [
        (1, "Biscuit", "gotcha_day", True),
        (2, "Ruth", "birthday", False),
        (12, "Biscuit", "birthday", True),
    ]  # people never get gotcha days
    assert out[1].link == "/app/u/ruth"
    repo.user_birthdays.assert_awaited_with(CID, viewer.id)
    house.visible.assert_awaited_with(viewer.id, CID)
    with pytest.raises(ValidationError):
        await svc.in_range(viewer, date(2026, 1, 1), date(2027, 6, 1))


async def test_memorialized_and_passed_emit_remembrance():
    repo, house = AsyncMock(), AsyncMock()
    repo.user_birthdays.return_value = []
    repo.memorialized_users.return_value = [
        (uuid.uuid4(), "ruth", "Ruth", date(1931, 12, 2), date(2026, 6, 1))
    ]
    pet = SimpleNamespace(
        id=uuid.uuid4(),
        kind="pet",
        name="Biscuit",
        birthday=date(2010, 12, 12),
        gotcha_day=date(2011, 12, 20),
        passed_on=date(2025, 12, 25),
    )
    house.visible.return_value = [pet]
    out = await CelebrationService(repo, house, CID).in_range(
        SimpleNamespace(id=uuid.uuid4()), date(2026, 12, 1), date(2026, 12, 31)
    )
    assert [(c.date.day, c.occasion, c.title) for c in out] == [
        (2, "remembrance", "Remembering Ruth"),
        (12, "remembrance", "Remembering Biscuit"),
        (25, "remembrance", "Remembering Biscuit"),
    ]  # passed pet: no gotcha day
