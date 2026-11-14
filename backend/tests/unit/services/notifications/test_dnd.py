"""
@file test_dnd.py
@brief Unit tests for the DnD evaluator, channel gating and snooze parsing.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import AppError
from app.services.notifications import registry
from app.services.notifications import types as _types  # noqa: F401
from app.services.notifications.dnd import gate_channels, in_dnd, resolve_snooze

NIGHT = {"mon": [{"start": "22:00", "end": "07:00"}]}


def _utc(*a: int) -> datetime:
    return datetime(*a, tzinfo=UTC)


class TestInDnd:
    def test_no_schedule_no_snooze(self):
        assert in_dnd(None, None, "UTC", _utc(2026, 1, 5, 12)) is False

    def test_snooze_active(self):
        now = _utc(2026, 1, 5, 12)
        assert in_dnd(None, now + timedelta(hours=1), "UTC", now) is True

    def test_snooze_expired(self):
        now = _utc(2026, 1, 5, 12)
        assert in_dnd(None, now - timedelta(minutes=1), "UTC", now) is False

    def test_overnight_evening_part(self):
        assert in_dnd(NIGHT, None, "UTC", _utc(2026, 1, 5, 23)) is True  # Monday

    def test_overnight_morning_spill_next_day(self):
        assert in_dnd(NIGHT, None, "UTC", _utc(2026, 1, 6, 6, 59)) is True  # Tuesday

    def test_overnight_end_exclusive(self):
        assert in_dnd(NIGHT, None, "UTC", _utc(2026, 1, 6, 7)) is False

    def test_outside_window(self):
        assert in_dnd(NIGHT, None, "UTC", _utc(2026, 1, 5, 12)) is False

    def test_other_day_not_matched(self):
        assert in_dnd(NIGHT, None, "UTC", _utc(2026, 1, 7, 23)) is False  # Wednesday

    def test_same_day_window(self):
        sched = {"tue": [{"start": "09:00", "end": "17:00"}]}
        assert in_dnd(sched, None, "UTC", _utc(2026, 1, 6, 10)) is True
        assert in_dnd(sched, None, "UTC", _utc(2026, 1, 6, 18)) is False

    def test_multiple_windows(self):
        sched = {"mon": [{"start": "08:00", "end": "09:00"}, {"start": "12:00", "end": "13:00"}]}
        assert in_dnd(sched, None, "UTC", _utc(2026, 1, 5, 12, 30)) is True
        assert in_dnd(sched, None, "UTC", _utc(2026, 1, 5, 10)) is False

    def test_timezone_conversion(self):
        # 03:00 UTC Tue == 22:00 Mon in New York (EST, UTC-5)
        assert in_dnd(NIGHT, None, "America/New_York", _utc(2026, 1, 6, 3)) is True
        assert in_dnd(NIGHT, None, "UTC", _utc(2026, 1, 6, 3)) is True
        assert in_dnd(NIGHT, None, "Asia/Tokyo", _utc(2026, 1, 5, 3)) is False

    def test_dst_offset_applied(self):
        sched = {"sat": [{"start": "22:00", "end": "23:00"}]}
        # Summer (EDT, UTC-4): 02:30 UTC Sun == 22:30 Sat local
        assert in_dnd(sched, None, "America/New_York", _utc(2026, 7, 5, 2, 30)) is True
        # Winter (EST, UTC-5): same UTC time is 21:30 local
        assert in_dnd(sched, None, "America/New_York", _utc(2026, 1, 11, 2, 30)) is False

    def test_naive_now_treated_as_utc(self):
        assert in_dnd(NIGHT, None, "UTC", datetime(2026, 1, 5, 23)) is True

    def test_non_dict_window_ignored(self):
        assert in_dnd({"mon": ["22:00-07:00"]}, None, "UTC", _utc(2026, 1, 5, 23)) is False

    def test_malformed_schedule_ignored(self):
        assert in_dnd({"mon": [{"start": "bad"}]}, None, "UTC", _utc(2026, 1, 5, 23)) is False


class TestGateChannels:
    EFF = {"inapp": True, "email": True, "push": True, "toast": True}

    def test_unchanged_when_not_dnd(self):
        t = registry.get("mention")
        assert gate_channels(self.EFF, t, False) == self.EFF

    def test_suppresses_outbound_in_dnd(self):
        t = registry.get("mention")
        out = gate_channels(self.EFF, t, True)
        assert out == {"inapp": True, "email": False, "push": False, "toast": False}

    def test_bypass_type_unchanged(self):
        t = registry.get("system")
        assert t.bypass_dnd
        assert gate_channels(self.EFF, t, True) == self.EFF

    def test_does_not_mutate_input(self):
        gate_channels(self.EFF, registry.get("mention"), True)
        assert self.EFF["email"] is True


class TestResolveSnooze:
    NOW = _utc(2026, 1, 5, 12)

    def test_one_hour(self):
        assert resolve_snooze("1h", "UTC", self.NOW) == self.NOW + timedelta(hours=1)

    def test_until_morning_next_day(self):
        assert resolve_snooze("until_morning", "UTC", self.NOW) == _utc(2026, 1, 6, 7)

    def test_until_morning_same_day_when_early(self):
        now = _utc(2026, 1, 5, 3)
        assert resolve_snooze("until_morning", "UTC", now) == _utc(2026, 1, 5, 7)

    def test_until_morning_tz(self):
        got = resolve_snooze("until_morning", "America/New_York", self.NOW)
        assert got == _utc(2026, 1, 6, 12)  # 07:00 EST

    def test_iso8601(self):
        got = resolve_snooze("2026-01-05T18:00:00+00:00", "UTC", self.NOW)
        assert got == _utc(2026, 1, 5, 18)

    def test_iso_naive_treated_as_utc(self):
        assert resolve_snooze("2026-01-05T18:00:00", "UTC", self.NOW) == _utc(2026, 1, 5, 18)

    def test_iso_past_rejected(self):
        with pytest.raises(AppError) as e:
            resolve_snooze("2026-01-05T11:00:00+00:00", "UTC", self.NOW)
        assert e.value.status_code == 400

    def test_garbage_rejected(self):
        with pytest.raises(AppError) as e:
            resolve_snooze("soon", "UTC", self.NOW)
        assert e.value.status_code == 400
