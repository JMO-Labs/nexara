"""@file Do-Not-Disturb evaluation, channel gating and snooze parsing.

@brief Pure helpers; schedule shape is ``{"mon": [{"start": "22:00", "end": "07:00"}]}``
with day keys ``mon..sun`` and local ``HH:MM`` times in the user's timezone.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.core.exceptions import AppError
from app.services.notifications.registry import Channel, NotificationType

_DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_SUPPRESSED: tuple[Channel, ...] = ("email", "push", "toast")
MORNING = time(7, 0)
"""@brief Local time that ``until_morning`` snoozes resolve to."""


def _parse(value: Any) -> time | None:
    try:
        return time.fromisoformat(str(value))
    except ValueError:
        return None


def _in_window(window: Any, local: time, *, spill: bool) -> bool:
    """@brief Test one window; ``spill`` selects the previous day's overnight tail."""
    if not isinstance(window, dict):
        return False
    start, end = _parse(window.get("start")), _parse(window.get("end"))
    if start is None or end is None or start == end:
        return False
    if start < end:
        return not spill and start <= local < end
    return local < end if spill else local >= start


def in_dnd(
    schedule: dict[str, Any] | None,
    until: datetime | None,
    tz: str,
    now: datetime,
) -> bool:
    """@brief Whether the user is in Do-Not-Disturb at ``now``.

    @param schedule Weekly windows or None.
    @param until Snooze end or None.
    @param tz IANA timezone of the schedule.
    @param now Current instant (naive values are taken as UTC).
    @return True if snoozed or inside a scheduled window (overnight aware).
    """
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    if until is not None and until > now:
        return True
    if not schedule:
        return False
    local = now.astimezone(ZoneInfo(tz))
    idx = local.weekday()
    t = local.time()
    today = schedule.get(_DAYS[idx]) or []
    yesterday = schedule.get(_DAYS[idx - 1]) or []
    return any(_in_window(w, t, spill=False) for w in today) or any(
        _in_window(w, t, spill=True) for w in yesterday
    )


def gate_channels(
    effective: dict[Channel, bool],
    type: NotificationType,  # noqa: A002
    in_dnd_now: bool,
) -> dict[Channel, bool]:
    """@brief Suppress email/push/toast during DnD unless the type bypasses it.

    @return A new map; in-app delivery is always kept as-is.
    """
    out = dict(effective)
    if in_dnd_now and not type.bypass_dnd:
        for ch in _SUPPRESSED:
            out[ch] = False
    return out


def resolve_snooze(duration: str, tz: str, now: datetime) -> datetime:
    """@brief Turn ``1h`` / ``until_morning`` / ISO-8601 into an aware end instant.

    @throws AppError NOTIF_PREF_INVALID (400) if unparseable or not in the future.
    """
    if duration == "1h":
        return now + timedelta(hours=1)
    if duration == "until_morning":
        zone = ZoneInfo(tz)
        local = now.astimezone(zone)
        target = datetime.combine(local.date(), MORNING, tzinfo=zone)
        if target <= local:
            target = datetime.combine(local.date() + timedelta(days=1), MORNING, tzinfo=zone)
        return target.astimezone(UTC)
    try:
        parsed = datetime.fromisoformat(duration)
    except ValueError:
        raise _bad(f"Invalid snooze duration: {duration}") from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    if parsed <= now:
        raise _bad("Snooze end must be in the future")
    return parsed


def _bad(message: str) -> AppError:
    return AppError(
        code="NOTIF_PREF_INVALID",
        message=message,
        status_code=400,
        details={"field": "duration"},
    )
