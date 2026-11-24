"""
@file test_countdown_service.py
@brief Unit tests: countdown date math, reminders and Home filtering (mocked repo).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

from app.models.countdown import Countdown
from app.repositories.countdown_repo import CountdownRepository
from app.services.countdown_service import (
    CountdownService,
    days_left,
    next_occurrence,
    reminder_text,
)

CID = uuid.uuid4()


def _c(target: date, yearly: bool = False, title: str = "Dad's retirement") -> MagicMock:
    c = MagicMock(spec=Countdown)
    c.id, c.author_id, c.title = uuid.uuid4(), uuid.uuid4(), title
    c.target_date, c.repeat_yearly = target, yearly
    return c


def test_yearly_feb29_rolls_to_feb28_next_year():
    c = _c(date(2024, 2, 29), yearly=True)
    assert next_occurrence(c, date(2025, 3, 1)) == date(2026, 2, 28)
    assert next_occurrence(c, date(2027, 1, 1)) == date(2027, 2, 28)
    assert next_occurrence(c, date(2028, 1, 1)) == date(2028, 2, 29)


def test_yearly_restarts_day_after_and_oneoff_stays():
    c = _c(date(2025, 6, 10), yearly=True)
    assert days_left(c, date(2026, 6, 10)) == 0
    assert next_occurrence(c, date(2026, 6, 11)) == date(2027, 6, 10)
    assert days_left(_c(date(2025, 6, 10)), date(2025, 6, 14)) == -4


def test_reminder_text():
    c = _c(date(2025, 1, 1))
    assert reminder_text(c, 7) == "7 days until Dad's retirement"
    assert reminder_text(c, 1) == "Tomorrow: Dad's retirement"
    assert reminder_text(c, 0) == "Today: Dad's retirement!"


async def test_reminder_sent_once_per_kind_and_viewer_tz():
    repo = AsyncMock(spec=CountdownRepository)
    uid = uuid.uuid4()
    c = _c(date(2026, 6, 10))
    repo.reminder_targets.return_value = [(c, uid, "Pacific/Auckland")]
    repo.mark_sent.side_effect = [True, False]
    notifier = MagicMock(notify=AsyncMock())
    svc = CountdownService(repo, CID, notifier)
    # 2026-06-02 20:00 UTC is already 06-03 in Auckland -> 7 days left
    now = datetime(2026, 6, 2, 20, tzinfo=UTC)
    assert await svc.send_reminders(now) == 1
    assert await svc.send_reminders(now) == 0
    assert notifier.notify.await_count == 1
    assert repo.mark_sent.await_args.args[2:] == ("d7", date(2026, 6, 10))
    kw = notifier.notify.await_args.kwargs
    assert kw["type"] == "countdown_reminder" and kw["payload"]["link"].endswith(str(c.id))


async def test_no_reminder_off_schedule():
    repo = AsyncMock(spec=CountdownRepository)
    repo.reminder_targets.return_value = [(_c(date(2026, 6, 10)), uuid.uuid4(), None)]
    svc = CountdownService(repo, CID, MagicMock(notify=AsyncMock()))
    assert await svc.send_reminders(datetime(2026, 6, 5, 12, tzinfo=UTC)) == 0
