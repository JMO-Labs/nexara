"""
@file test_birthday_tasks.py
@brief Unit tests for the birthday reminder Celery task and Beat entry.
"""

from app.tasks.birthday_tasks import send_birthday_reminders
from app.tasks.celery_app import celery_app


def test_task_name_and_queue():
    assert send_birthday_reminders.name == "app.tasks.birthday_tasks.send_birthday_reminders"
    assert send_birthday_reminders.queue == "notifications"


def test_beat_schedule_daily_0600():
    entry = celery_app.conf.beat_schedule["send-birthday-reminders"]
    assert entry["task"] == send_birthday_reminders.name
    sched = entry["schedule"]
    assert sched.hour == {6} and sched.minute == {0}
