"""
@file test_models_social.py
@brief TDD tests for social models: Subgroup, Event, Chat, Notification.
"""

import app.models  # noqa: F401 — register all models with Base.metadata
from app.db.base import Base


def _get_table(name: str):
    """@brief Helper to retrieve a table from Base metadata by name."""
    return Base.metadata.tables.get(name)


def _get_columns(table_name: str) -> set[str]:
    """@brief Return the set of column names for a given table."""
    table = _get_table(table_name)
    assert table is not None, f"Table '{table_name}' not found in metadata"
    return {c.name for c in table.columns}


class TestSubgroupModel:
    """@brief Verify the subgroups table schema."""

    def test_table_exists(self):
        assert _get_table("subgroups") is not None

    def test_required_columns(self):
        cols = _get_columns("subgroups")
        expected = {
            "id",
            "community_id",
            "name",
            "slug",
            "description",
            "is_private",
            "join_policy",
            "created_by",
            "archived_at",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(cols)


class TestSubgroupMemberModel:
    """@brief Verify the subgroup_members table schema."""

    def test_table_exists(self):
        assert _get_table("subgroup_members") is not None

    def test_composite_pk(self):
        table = _get_table("subgroup_members")
        pk_names = {c.name for c in table.primary_key.columns}
        assert pk_names == {"subgroup_id", "user_id"}


class TestChatChannelModel:
    """@brief Verify the chat_channels table schema."""

    def test_table_exists(self):
        assert _get_table("chat_channels") is not None

    def test_required_columns(self):
        cols = _get_columns("chat_channels")
        expected = {"id", "community_id", "name", "channel_type", "created_at"}
        assert expected.issubset(cols)


class TestEventModel:
    """@brief Verify the events table schema."""

    def test_table_exists(self):
        assert _get_table("events") is not None

    def test_required_columns(self):
        cols = _get_columns("events")
        expected = {
            "id",
            "community_id",
            "author_id",
            "title",
            "starts_at",
            "ends_at",
            "is_all_day",
            "recurrence_rule",
            "ical_uid",
            "visibility",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(cols)


class TestEventAttendanceModel:
    """@brief Verify the event_attendance table schema."""

    def test_table_exists(self):
        assert _get_table("event_attendance") is not None

    def test_required_columns(self):
        cols = _get_columns("event_attendance")
        expected = {"id", "community_id", "event_id", "user_id", "status"}
        assert expected.issubset(cols)


class TestCalendarSubscriptionModel:
    """@brief Verify the calendar_subscriptions table schema."""

    def test_table_exists(self):
        assert _get_table("calendar_subscriptions") is not None

    def test_required_columns(self):
        cols = _get_columns("calendar_subscriptions")
        expected = {
            "id",
            "community_id",
            "user_id",
            "name",
            "source_type",
            "sync_enabled",
            "created_at",
        }
        assert expected.issubset(cols)


class TestChatMessageModel:
    """@brief Verify the chat_messages table schema."""

    def test_table_exists(self):
        assert _get_table("chat_messages") is not None

    def test_required_columns(self):
        cols = _get_columns("chat_messages")
        expected = {"id", "community_id", "author_id", "content", "content_fts", "created_at"}
        assert expected.issubset(cols)


class TestNotificationModel:
    """@brief Verify the notifications table schema."""

    def test_table_exists(self):
        assert _get_table("notifications") is not None

    def test_required_columns(self):
        cols = _get_columns("notifications")
        expected = {"id", "community_id", "user_id", "type", "payload", "read_at", "created_at"}
        assert expected.issubset(cols)


class TestPushSubscriptionModel:
    """@brief Verify the push_subscriptions table schema."""

    def test_table_exists(self):
        assert _get_table("push_subscriptions") is not None

    def test_required_columns(self):
        cols = _get_columns("push_subscriptions")
        expected = {"id", "user_id", "endpoint", "p256dh", "auth", "created_at"}
        assert expected.issubset(cols)
