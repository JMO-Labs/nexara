"""
@file test_story_tasks.py
@brief Beat schedule/route and notification registration for stories.
"""

from celery.schedules import crontab

from app.services.notification_service import PREF_MAP
from app.services.notifications import registry
from app.tasks.celery_app import celery_app


def test_daily_beat_and_route():
    entry = celery_app.conf.beat_schedule["stories-daily"]
    assert entry["task"] == "stories.daily"
    assert entry["schedule"] == crontab(hour=9, minute=0)
    assert celery_app.amqp.router.route({}, "stories.daily")["queue"].name == "notifications"


def test_notification_types_registered_with_prefs():
    for key in ("story_request", "story_answered"):
        assert registry.get(key).key == key
        assert key in PREF_MAP
