"""
@file test_retention_tasks.py
@brief Unit tests for retention_tasks: storage snapshots, aging, and purge tasks.
"""

from __future__ import annotations

import pytest


class TestTakeStorageSnapshot:
    """@brief Tests for take_storage_snapshot task."""

    def test_task_name(self):
        from app.tasks.retention_tasks import take_storage_snapshot
        assert take_storage_snapshot.name == "app.tasks.retention_tasks.take_storage_snapshot"

    def test_queue_is_maintenance(self):
        from app.tasks.retention_tasks import take_storage_snapshot
        assert take_storage_snapshot.queue == "maintenance"

    def test_returns_status(self):
        from app.tasks.retention_tasks import take_storage_snapshot
        result = take_storage_snapshot()
        assert result == {"status": "completed"}


class TestAgeChatMessages:
    """@brief Tests for age_chat_messages task."""

    def test_task_name(self):
        from app.tasks.retention_tasks import age_chat_messages
        assert age_chat_messages.name == "app.tasks.retention_tasks.age_chat_messages"

    def test_returns_count(self):
        from app.tasks.retention_tasks import age_chat_messages
        result = age_chat_messages()
        assert "deleted_count" in result


class TestAgeNotifications:
    """@brief Tests for age_notifications task."""

    def test_task_name(self):
        from app.tasks.retention_tasks import age_notifications
        assert age_notifications.name == "app.tasks.retention_tasks.age_notifications"

    def test_returns_count(self):
        from app.tasks.retention_tasks import age_notifications
        result = age_notifications()
        assert "deleted_count" in result


class TestPurgeSoftDeletedPosts:
    """@brief Tests for purge_soft_deleted_posts task."""

    def test_task_name(self):
        from app.tasks.retention_tasks import purge_soft_deleted_posts
        assert purge_soft_deleted_posts.name == "app.tasks.retention_tasks.purge_soft_deleted_posts"

    def test_returns_count(self):
        from app.tasks.retention_tasks import purge_soft_deleted_posts
        result = purge_soft_deleted_posts()
        assert "deleted_count" in result


class TestPurgeSoftDeletedUsers:
    """@brief Tests for purge_soft_deleted_users task."""

    def test_task_name(self):
        from app.tasks.retention_tasks import purge_soft_deleted_users
        assert purge_soft_deleted_users.name == "app.tasks.retention_tasks.purge_soft_deleted_users"

    def test_returns_count(self):
        from app.tasks.retention_tasks import purge_soft_deleted_users
        result = purge_soft_deleted_users()
        assert "deleted_count" in result


class TestCleanupExpiredLinkPreviews:
    """@brief Tests for cleanup_expired_link_previews task."""

    def test_task_name(self):
        from app.tasks.retention_tasks import cleanup_expired_link_previews
        assert cleanup_expired_link_previews.name == "app.tasks.retention_tasks.cleanup_expired_link_previews"

    def test_returns_count(self):
        from app.tasks.retention_tasks import cleanup_expired_link_previews
        result = cleanup_expired_link_previews()
        assert "deleted_count" in result


class TestAgeAuditLogs:
    """@brief Tests for age_audit_logs task."""

    def test_task_name(self):
        from app.tasks.retention_tasks import age_audit_logs
        assert age_audit_logs.name == "app.tasks.retention_tasks.age_audit_logs"

    def test_returns_count(self):
        from app.tasks.retention_tasks import age_audit_logs
        result = age_audit_logs()
        assert "deleted_count" in result


class TestAgeAiUsageLogs:
    """@brief Tests for age_ai_usage_logs task."""

    def test_task_name(self):
        from app.tasks.retention_tasks import age_ai_usage_logs
        assert age_ai_usage_logs.name == "app.tasks.retention_tasks.age_ai_usage_logs"

    def test_returns_count(self):
        from app.tasks.retention_tasks import age_ai_usage_logs
        result = age_ai_usage_logs()
        assert "deleted_count" in result


class TestAgePostMedia:
    """@brief Tests for age_post_media task."""

    def test_task_name(self):
        from app.tasks.retention_tasks import age_post_media
        assert age_post_media.name == "app.tasks.retention_tasks.age_post_media"

    def test_returns_count(self):
        from app.tasks.retention_tasks import age_post_media
        result = age_post_media()
        assert "deleted_count" in result


class TestAgePosts:
    """@brief Tests for age_posts task."""

    def test_task_name(self):
        from app.tasks.retention_tasks import age_posts
        assert age_posts.name == "app.tasks.retention_tasks.age_posts"

    def test_returns_count(self):
        from app.tasks.retention_tasks import age_posts
        result = age_posts()
        assert "deleted_count" in result


class TestRetentionTasksRouting:
    """@brief Verify all retention tasks are routed to the maintenance queue."""

    def test_all_tasks_on_maintenance_queue(self):
        from app.tasks.retention_tasks import (
            age_ai_usage_logs,
            age_audit_logs,
            age_chat_messages,
            age_notifications,
            age_post_media,
            age_posts,
            cleanup_expired_link_previews,
            purge_soft_deleted_posts,
            purge_soft_deleted_users,
            take_storage_snapshot,
        )

        tasks = [
            take_storage_snapshot,
            age_chat_messages,
            age_notifications,
            purge_soft_deleted_posts,
            purge_soft_deleted_users,
            cleanup_expired_link_previews,
            age_audit_logs,
            age_ai_usage_logs,
            age_post_media,
            age_posts,
        ]
        for task in tasks:
            assert task.queue == "maintenance", f"{task.name} not on maintenance queue"
