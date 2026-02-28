"""
@file test_celery_app.py
@brief Unit tests for the Celery application configuration.
"""

from app.tasks.celery_app import celery_app


class TestCeleryConfig:
    """@brief Verify Celery configuration values."""

    def test_broker_url_uses_db_zero(self):
        assert "/0" in celery_app.conf.broker_url

    def test_serializer_is_json(self):
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content

    def test_timezone_is_utc(self):
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_acks_late_enabled(self):
        assert celery_app.conf.task_acks_late is True

    def test_prefetch_multiplier_is_one(self):
        assert celery_app.conf.worker_prefetch_multiplier == 1

    def test_reject_on_worker_lost(self):
        assert celery_app.conf.task_reject_on_worker_lost is True

    def test_result_expires(self):
        assert celery_app.conf.result_expires == 3600

    def test_time_limits(self):
        assert celery_app.conf.task_soft_time_limit == 60
        assert celery_app.conf.task_time_limit == 120

    def test_task_routing_keys(self):
        routes = celery_app.conf.task_routes
        assert "app.tasks.email_tasks.*" in routes
        assert "app.tasks.media_tasks.*" in routes
        assert "app.tasks.notification_tasks.*" in routes
        assert "app.tasks.maintenance_tasks.*" in routes

    def test_email_tasks_routed_to_email_queue(self):
        routes = celery_app.conf.task_routes
        assert routes["app.tasks.email_tasks.*"]["queue"] == "email"

    def test_media_tasks_routed_to_media_queue(self):
        routes = celery_app.conf.task_routes
        assert routes["app.tasks.media_tasks.*"]["queue"] == "media"


class TestBeatSchedule:
    """@brief Verify Beat periodic task schedule."""

    def test_beat_schedule_not_empty(self):
        assert len(celery_app.conf.beat_schedule) > 0

    def test_cleanup_expired_tokens_scheduled(self):
        assert "cleanup-expired-tokens" in celery_app.conf.beat_schedule

    def test_recalculate_quotas_scheduled(self):
        assert "recalculate-quotas" in celery_app.conf.beat_schedule

    def test_orphaned_media_cleanup_scheduled(self):
        assert "cleanup-orphaned-media" in celery_app.conf.beat_schedule

    def test_event_reminders_scheduled(self):
        assert "dispatch-event-reminders" in celery_app.conf.beat_schedule

    def test_refresh_prometheus_gauges_scheduled(self):
        assert "refresh-prometheus-gauges" in celery_app.conf.beat_schedule

    def test_prometheus_gauges_runs_every_60_seconds(self):
        entry = celery_app.conf.beat_schedule["refresh-prometheus-gauges"]
        assert entry["schedule"] == 60.0

    def test_database_backup_scheduled(self):
        assert "database-backup" in celery_app.conf.beat_schedule
