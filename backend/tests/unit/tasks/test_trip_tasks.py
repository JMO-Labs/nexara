"""
@file test_trip_tasks.py
@brief Beat wiring for trips.sweep.
"""

from celery.schedules import crontab

from app.tasks.celery_app import celery_app


def test_beat_schedule_and_route() -> None:
    entry = celery_app.conf.beat_schedule["trips-sweep"]
    assert entry["task"] == "trips.sweep"
    assert entry["schedule"] == crontab(minute="*/5")
    assert celery_app.amqp.router.route({}, "trips.sweep")["queue"].name == "notifications"
