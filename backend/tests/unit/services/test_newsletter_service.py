"""
@file test_newsletter_service.py
@brief Month parsing, bounds in the viewer's timezone, and range checks.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.exceptions import NotFoundError
from app.services.newsletter_service import check_month, month_bounds, parse_month

NOW = datetime(2026, 11, 22, 12, tzinfo=UTC)
CREATED = datetime(2025, 3, 5, tzinfo=UTC)


def test_bounds_use_viewer_timezone() -> None:
    start, end = month_bounds("2026-11", "America/New_York")
    assert start == datetime(2026, 11, 1, 4, tzinfo=UTC)
    assert end == datetime(2026, 12, 1, 5, tzinfo=UTC)


def test_bounds_december_rolls_year_and_bad_tz_is_utc() -> None:
    start, end = month_bounds("2026-12", "Nope/Zone")
    assert start == datetime(2026, 12, 1, tzinfo=UTC)
    assert end == datetime(2027, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize("bad", ["2026-13", "2026-1", "x", "2026-00", "2026-11-01"])
def test_parse_rejects_bad(bad: str) -> None:
    with pytest.raises(NotFoundError):
        parse_month(bad)


def test_check_month_range() -> None:
    check_month("2026-11", None, CREATED, NOW)
    check_month("2025-03", None, CREATED, NOW)
    for bad in ("2026-12", "2025-02"):
        with pytest.raises(NotFoundError):
            check_month(bad, None, CREATED, NOW)


def test_check_month_uses_viewer_zone_for_current_month() -> None:
    late = datetime(2026, 11, 30, 23, 30, tzinfo=UTC)
    check_month("2026-12", "Pacific/Auckland", CREATED, late)  # already December there
    with pytest.raises(NotFoundError):
        check_month("2026-12", "UTC", CREATED, late)
