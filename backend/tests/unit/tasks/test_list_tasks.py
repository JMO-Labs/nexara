"""
@file test_list_tasks.py
@brief Tests for list expiry/reminder Celery tasks and Beat schedule.
"""

import re
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from celery.schedules import crontab
from sqlalchemy.dialects import postgresql

from app.tasks import list_tasks
from app.tasks.celery_app import celery_app


def _entry(task: str) -> dict:
    entries = [e for e in celery_app.conf.beat_schedule.values() if e["task"] == task]
    assert len(entries) == 1
    return entries[0]


def test_beat_schedule_times():
    sweep = _entry("app.tasks.list_tasks.sweep_list_expirations")["schedule"]
    remind = _entry("app.tasks.list_tasks.dispatch_list_expiry_reminders")["schedule"]
    assert sweep == crontab(hour=2, minute=0)
    assert remind == crontab(hour=8, minute=0)


def test_tasks_routed_to_maintenance():
    for name in ("sweep_list_expirations", "dispatch_list_expiry_reminders"):
        full = f"app.tasks.list_tasks.{name}"
        assert full in celery_app.tasks
        route = celery_app.amqp.router.route({}, full)
        assert route["queue"].name == "maintenance"


def _lst(**kw):
    lst = MagicMock()
    lst.id = uuid.uuid4()
    lst.community_id = uuid.uuid4()
    lst.owner_id = uuid.uuid4()
    lst.title = "Potluck"
    lst.status = "active"
    lst.notified_at = None
    lst.expires_at = datetime.now(UTC)
    for k, v in kw.items():
        setattr(lst, k, v)
    return lst


def _session(batches, member_ids):
    session = AsyncMock()
    results = []
    for b in batches:
        r = MagicMock()
        r.scalars.return_value.all.return_value = b
        results.append(r)
    session.execute = AsyncMock(side_effect=results)
    session.scalars = AsyncMock(return_value=MagicMock(all=lambda: member_ids))
    return session


async def test_sweep_expires_notifies_owner_and_members_and_emits():
    lst = _lst()
    member = uuid.uuid4()
    session = _session([[lst], []], [member, lst.owner_id])
    notifier = AsyncMock()
    bus = AsyncMock()

    count = await list_tasks.sweep_expired_lists(session, lambda cid: notifier, bus, batch_size=100)

    assert count == 1
    assert lst.status == "expired"
    notified = {c.args[0] for c in notifier.notify.await_args_list}
    assert notified == {lst.owner_id, member}
    bus.emit.assert_awaited_once()
    session.commit.assert_awaited()


async def test_reminders_set_notified_at_and_notify():
    lst = _lst()
    session = _session([[lst], []], [])
    notifier = AsyncMock()
    bus = AsyncMock()

    count = await list_tasks.send_expiry_reminders(
        session, lambda cid: notifier, bus, batch_size=100
    )

    assert count == 1
    assert lst.notified_at is not None
    notifier.notify.assert_awaited_once()
    assert notifier.notify.await_args.args[0] == lst.owner_id


def test_entries_run_async(monkeypatch):
    async def fake() -> dict[str, int]:
        return {"expired": 2}

    monkeypatch.setattr(list_tasks, "_sweep_async", fake)
    assert list_tasks.sweep_list_expirations() == {"expired": 2}

    async def fake2() -> dict[str, int]:
        return {"reminded": 1}

    monkeypatch.setattr(list_tasks, "_remind_async", fake2)
    assert list_tasks.dispatch_list_expiry_reminders() == {"reminded": 1}


NOW = datetime(2026, 11, 13, 15, 30, tzinfo=UTC)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        return NOW


def _sql(stmt) -> str:
    """Compile for Postgres and inline params as ``<repr>`` tokens."""
    compiled = stmt.compile(dialect=postgresql.dialect())
    params = {
        k: datetime.fromisoformat(v.isoformat()) if isinstance(v, datetime) else v
        for k, v in compiled.params.items()
    }
    text = re.sub(r"%\((\w+)\)s", lambda m: f"<{params[m.group(1)]!r}>", str(compiled))
    return " ".join(text.replace('"', "").split())


async def _captured_sql(monkeypatch, fn) -> str:
    monkeypatch.setattr(list_tasks, "datetime", _FrozenDatetime)
    session = _session([[]], [])
    await fn(session, lambda cid: AsyncMock(), AsyncMock(), batch_size=7)
    return _sql(session.execute.await_args.args[0])


@pytest.mark.parametrize("fn", [list_tasks.sweep_expired_lists, list_tasks.send_expiry_reminders])
async def test_common_filters_locking_and_limit(monkeypatch, fn):
    sql = await _captured_sql(monkeypatch, fn)
    assert "list.status = <'active'>" in sql
    assert "list.deleted_at IS NULL" in sql
    assert "list.expires_at IS NOT NULL" in sql
    assert "LIMIT <7>" in sql
    assert sql.endswith("FOR UPDATE SKIP LOCKED")


async def test_sweep_selects_only_past_expiry(monkeypatch):
    sql = await _captured_sql(monkeypatch, list_tasks.sweep_expired_lists)
    where = sql.split(" WHERE ", 1)[1]
    assert f"list.expires_at < <{NOW!r}>" in where
    assert "list.expires_at >" not in where
    assert "notified_at" not in where


async def test_reminders_select_next_day_window_not_reminded_today(monkeypatch):
    sql = await _captured_sql(monkeypatch, list_tasks.send_expiry_reminders)
    today = datetime(2026, 11, 13, tzinfo=UTC)
    assert f"list.expires_at >= <{NOW!r}>" in sql
    assert f"list.expires_at <= <{NOW + timedelta(days=1)!r}>" in sql
    assert f"(list.notified_at IS NULL OR list.notified_at < <{today!r}>)" in sql
