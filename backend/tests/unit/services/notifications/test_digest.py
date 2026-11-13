"""
@file test_digest.py
@brief Tests for digest cadence evaluation.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.services.notifications.digest import should_send_now

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize("c", ["instant", "off"])
def test_instant_off_never(c):
    assert should_send_now(c, None, NOW, "UTC") is False


def test_hourly_never_sent():
    assert should_send_now("hourly", None, NOW, "UTC") is True


def test_hourly_boundary():
    assert should_send_now("hourly", NOW - timedelta(hours=1), NOW, "UTC") is True
    assert should_send_now("hourly", NOW - timedelta(minutes=59), NOW, "UTC") is False


def test_daily_before_8_local():
    now = datetime(2026, 11, 13, 7, 59, tzinfo=UTC)
    assert should_send_now("daily", None, now, "UTC") is False


def test_daily_at_8_local_never_sent():
    now = datetime(2026, 11, 13, 8, 0, tzinfo=UTC)
    assert should_send_now("daily", None, now, "UTC") is True


def test_daily_already_sent_today():
    last = datetime(2026, 11, 13, 8, 1, tzinfo=UTC)
    assert should_send_now("daily", last, NOW, "UTC") is False


def test_daily_sent_yesterday():
    assert should_send_now("daily", NOW - timedelta(days=1), NOW, "UTC") is True


def test_daily_tz_aware():
    # 12:00 UTC = 07:00 New York (EST) -> not yet; = 21:00 Tokyo -> yes
    assert should_send_now("daily", None, NOW, "America/New_York") is False
    assert should_send_now("daily", None, NOW, "Asia/Tokyo") is True


def test_daily_tz_date_boundary():
    # last sent 2026-11-13 03:00 UTC = 22:00 Nov 12 NY; now 14:00 UTC = 09:00 Nov 13 NY
    last = datetime(2026, 11, 13, 3, 0, tzinfo=UTC)
    now = datetime(2026, 11, 13, 14, 0, tzinfo=UTC)
    assert should_send_now("daily", last, now, "America/New_York") is True


def test_unknown_cadence_false():
    assert should_send_now("weekly", None, NOW, "UTC") is False


def test_bad_tz_falls_back_to_utc():
    assert should_send_now("daily", None, NOW, "Not/AZone") is True
