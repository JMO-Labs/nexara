"""
@file test_birthday_plausible.py
@brief Birthday must be 1900 or later and not in the future (profile + user update).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.profile import ProfileUpdate
from app.schemas.user import UserUpdateRequest


@pytest.mark.parametrize("model", [ProfileUpdate, UserUpdateRequest])
class TestBirthday:
    def test_partial_year_rejected(self, model) -> None:
        with pytest.raises(ValidationError):
            model(birthday=date(20, 5, 1))

    def test_before_1900_rejected(self, model) -> None:
        with pytest.raises(ValidationError):
            model(birthday=date(1899, 12, 31))

    def test_future_rejected(self, model) -> None:
        with pytest.raises(ValidationError):
            model(birthday=datetime.now(UTC).date() + timedelta(days=30))

    def test_plausible_and_null_ok(self, model) -> None:
        assert model(birthday=date(1900, 1, 1)).birthday == date(1900, 1, 1)
        assert model(birthday=datetime.now(UTC).date()).birthday is not None
        assert model(birthday=None).birthday is None
