"""
@file test_nudge_tasks.py
@brief Tests for nudge Celery task registration and Beat schedule.
"""

from app.tasks.celery_app import celery_app


def test_gentle_nudge_task_scheduled_daily():
    import app.tasks.nudge_tasks  # noqa: F401

    entries = [
        e
        for e in celery_app.conf.beat_schedule.values()
        if e["task"] == "app.tasks.nudge_tasks.send_gentle_nudges"
    ]
    assert len(entries) == 1
    assert "app.tasks.nudge_tasks.send_gentle_nudges" in celery_app.tasks


async def test_send_gentle_nudges_async_commits_and_returns_count(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock

    from app.tasks import nudge_tasks

    session = AsyncMock()
    factory = MagicMock()
    factory.return_value.__aenter__.return_value = session
    monkeypatch.setattr(nudge_tasks, "async_session_factory", factory)
    svc = MagicMock()
    svc.send_gentle_nudges = AsyncMock(return_value=3)
    monkeypatch.setattr(nudge_tasks, "NudgeService", MagicMock(return_value=svc))

    assert await nudge_tasks._send_gentle_nudges_async() == {"sent": 3}
    session.commit.assert_awaited_once()


def test_send_gentle_nudges_entry_runs_async(monkeypatch):
    from app.tasks import nudge_tasks

    async def fake() -> dict[str, int]:
        return {"sent": 2}

    monkeypatch.setattr(nudge_tasks, "_send_gentle_nudges_async", fake)
    assert nudge_tasks.send_gentle_nudges() == {"sent": 2}
