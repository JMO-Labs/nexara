"""
@file test_models_extended.py
@brief TDD tests for extended models: Gallery, Prompt, LinkPreview,
       Retention, Interest, Moderation, Branding, AuditLog.
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


class TestGalleryModel:
    """@brief Verify the galleries table schema."""

    def test_table_exists(self):
        assert _get_table("galleries") is not None

    def test_required_columns(self):
        cols = _get_columns("galleries")
        expected = {
            "id", "community_id", "owner_id", "title",
            "visibility", "contribution_policy", "item_count",
            "is_featured", "is_default", "is_event_gallery",
            "created_at", "updated_at",
        }
        assert expected.issubset(cols)


class TestGalleryItemModel:
    """@brief Verify the gallery_items table schema."""

    def test_table_exists(self):
        assert _get_table("gallery_items") is not None

    def test_required_columns(self):
        cols = _get_columns("gallery_items")
        expected = {"id", "community_id", "gallery_id", "media_id", "added_by", "position"}
        assert expected.issubset(cols)


class TestGalleryCollaboratorModel:
    """@brief Verify the gallery_collaborators table schema."""

    def test_table_exists(self):
        assert _get_table("gallery_collaborators") is not None

    def test_composite_pk(self):
        table = _get_table("gallery_collaborators")
        pk_names = {c.name for c in table.primary_key.columns}
        assert pk_names == {"gallery_id", "user_id"}


class TestPromptModel:
    """@brief Verify the prompts table schema."""

    def test_table_exists(self):
        assert _get_table("prompts") is not None

    def test_required_columns(self):
        cols = _get_columns("prompts")
        expected = {
            "id", "community_id", "title", "body", "source",
            "is_enabled", "frequency_type", "created_at",
        }
        assert expected.issubset(cols)


class TestPromptPostModel:
    """@brief Verify the prompt_posts table schema."""

    def test_table_exists(self):
        assert _get_table("prompt_posts") is not None

    def test_required_columns(self):
        cols = _get_columns("prompt_posts")
        expected = {
            "id", "community_id", "prompt_id", "post_id",
            "fired_at", "expires_at", "response_count", "is_finalised",
        }
        assert expected.issubset(cols)


class TestLinkPreviewModel:
    """@brief Verify the link_previews table schema."""

    def test_table_exists(self):
        assert _get_table("link_previews") is not None

    def test_required_columns(self):
        cols = _get_columns("link_previews")
        expected = {"id", "url", "url_hash", "title", "fetched_at", "expires_at"}
        assert expected.issubset(cols)


class TestPostLinkPreviewModel:
    """@brief Verify the post_link_previews junction table."""

    def test_table_exists(self):
        assert _get_table("post_link_previews") is not None

    def test_composite_pk(self):
        table = _get_table("post_link_previews")
        pk_names = {c.name for c in table.primary_key.columns}
        assert pk_names == {"post_id", "preview_id"}


class TestChatMessageLinkPreviewModel:
    """@brief Verify the chat_message_link_previews junction table."""

    def test_table_exists(self):
        assert _get_table("chat_message_link_previews") is not None

    def test_composite_pk(self):
        table = _get_table("chat_message_link_previews")
        pk_names = {c.name for c in table.primary_key.columns}
        assert pk_names == {"message_id", "preview_id"}


class TestRetentionPolicyModel:
    """@brief Verify the retention_policies table schema."""

    def test_table_exists(self):
        assert _get_table("retention_policies") is not None

    def test_pk_is_policy_key(self):
        table = _get_table("retention_policies")
        pk_names = [c.name for c in table.primary_key.columns]
        assert pk_names == ["policy_key"]


class TestStorageSnapshotModel:
    """@brief Verify the storage_snapshots table schema."""

    def test_table_exists(self):
        assert _get_table("storage_snapshots") is not None

    def test_required_columns(self):
        cols = _get_columns("storage_snapshots")
        expected = {"id", "snapshot_date", "total_bytes", "created_at"}
        assert expected.issubset(cols)


class TestStorageAlertModel:
    """@brief Verify the storage_alerts table schema."""

    def test_table_exists(self):
        assert _get_table("storage_alerts") is not None

    def test_required_columns(self):
        cols = _get_columns("storage_alerts")
        expected = {"id", "alert_type", "fired_at"}
        assert expected.issubset(cols)


class TestInterestCategoryModel:
    """@brief Verify the interest_categories table schema."""

    def test_table_exists(self):
        assert _get_table("interest_categories") is not None

    def test_pk_is_slug(self):
        table = _get_table("interest_categories")
        pk_names = [c.name for c in table.primary_key.columns]
        assert pk_names == ["slug"]


class TestUserInterestModel:
    """@brief Verify the user_interests table schema."""

    def test_table_exists(self):
        assert _get_table("user_interests") is not None

    def test_required_columns(self):
        cols = _get_columns("user_interests")
        expected = {"id", "user_id", "category_slug", "value", "source", "created_at"}
        assert expected.issubset(cols)


class TestContentReportModel:
    """@brief Verify the content_reports table schema."""

    def test_table_exists(self):
        assert _get_table("content_reports") is not None

    def test_required_columns(self):
        cols = _get_columns("content_reports")
        expected = {
            "id", "reporter_id", "target_type", "target_id",
            "reason", "status", "community_id", "created_at",
        }
        assert expected.issubset(cols)


class TestUserBlockModel:
    """@brief Verify the user_blocks table schema."""

    def test_table_exists(self):
        assert _get_table("user_blocks") is not None

    def test_required_columns(self):
        cols = _get_columns("user_blocks")
        expected = {"id", "blocker_id", "blocked_id", "community_id", "created_at"}
        assert expected.issubset(cols)


class TestCommunityBrandingModel:
    """@brief Verify the community_branding table schema."""

    def test_table_exists(self):
        assert _get_table("community_branding") is not None

    def test_branding_columns(self):
        cols = _get_columns("community_branding")
        expected = {
            "id", "community_id", "community_name", "tagline",
            "color_primary", "font_family", "updated_at",
        }
        assert expected.issubset(cols)


class TestAuditLogModel:
    """@brief Verify the audit_log table schema."""

    def test_table_exists(self):
        assert _get_table("audit_log") is not None

    def test_required_columns(self):
        cols = _get_columns("audit_log")
        expected = {"id", "actor_id", "action", "target_type", "target_id", "metadata", "created_at"}
        assert expected.issubset(cols)


class TestAllTablesRegistered:
    """@brief Verify all Phase 1 tables are registered in Base.metadata."""

    EXPECTED_TABLES = {
        "communities", "users", "user_settings", "refresh_tokens",
        "user_backup_codes", "invites", "posts", "comments", "reactions",
        "post_media", "media", "events", "event_attendance",
        "calendar_subscriptions", "subgroups", "subgroup_members",
        "chat_channels", "chat_messages", "notifications",
        "push_subscriptions", "galleries", "gallery_items",
        "gallery_collaborators", "prompts", "prompt_posts",
        "link_previews", "post_link_previews",
        "chat_message_link_previews", "retention_policies",
        "storage_snapshots", "storage_alerts", "interest_categories",
        "user_interests", "content_reports", "user_blocks",
        "community_branding", "audit_log",
    }

    def test_all_tables_present(self):
        registered = set(Base.metadata.tables.keys())
        missing = self.EXPECTED_TABLES - registered
        assert not missing, f"Missing tables: {missing}"
