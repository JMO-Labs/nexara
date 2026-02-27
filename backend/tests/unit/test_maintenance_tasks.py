"""
@file test_maintenance_tasks.py
@brief Unit tests for maintenance tasks.
"""

from app.tasks.maintenance_tasks import (
    cleanup_expired_tokens,
    database_backup,
    recalculate_storage_quotas,
    refresh_prometheus_gauges,
)


class TestRefreshPrometheusGauges:
    """@brief Verify Prometheus gauge refresh task."""

    def test_task_name(self):
        assert refresh_prometheus_gauges.name == "app.tasks.maintenance_tasks.refresh_prometheus_gauges"

    def test_queue_is_maintenance(self):
        assert refresh_prometheus_gauges.queue == "maintenance"

    def test_returns_status(self):
        result = refresh_prometheus_gauges()
        assert result["status"] == "refreshed"


class TestRecalculateStorageQuotas:
    """@brief Verify storage quota recalculation task."""

    def test_task_name(self):
        assert recalculate_storage_quotas.name == "app.tasks.maintenance_tasks.recalculate_storage_quotas"

    def test_returns_status(self):
        result = recalculate_storage_quotas()
        assert result["status"] == "recalculated"


class TestCleanupExpiredTokens:
    """@brief Verify expired token cleanup task."""

    def test_task_name(self):
        assert cleanup_expired_tokens.name == "app.tasks.maintenance_tasks.cleanup_expired_tokens"

    def test_returns_count(self):
        result = cleanup_expired_tokens()
        assert "deleted_count" in result


class TestDatabaseBackup:
    """@brief Verify database backup task."""

    def test_task_name(self):
        assert database_backup.name == "app.tasks.maintenance_tasks.database_backup"

    def test_time_limit(self):
        assert database_backup.time_limit == 1800

    def test_returns_status(self):
        result = database_backup()
        assert result["status"] == "completed"
