"""
@file digest.py
@brief Digest cadence evaluation.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DAILY_HOUR = 8
"""@brief Local hour at/after which a daily digest may be sent."""


def should_send_now(cadence: str, last_sent_at: datetime | None, now: datetime, tz: str) -> bool:
    """
    @brief Decide whether a digest is due.

    @param cadence instant | off | hourly | daily.
    @param last_sent_at Last digest send time (aware) or None.
    @param now Current aware time.
    @param tz IANA timezone name; invalid names fall back to UTC.
    @return True when a digest should be sent now.
    """
    if cadence == "hourly":
        return last_sent_at is None or now - last_sent_at >= timedelta(hours=1)
    if cadence == "daily":
        try:
            zone = ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError):
            zone = ZoneInfo("UTC")
        local = now.astimezone(zone)
        if local.hour < DAILY_HOUR:
            return False
        return last_sent_at is None or last_sent_at.astimezone(zone).date() < local.date()
    return False
