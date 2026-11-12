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
