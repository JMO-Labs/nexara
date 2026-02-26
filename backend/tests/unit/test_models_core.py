"""
@file test_models_core.py
@brief TDD tests for core models: Community, User, UserSettings, Auth, Invite.

These tests inspect SQLAlchemy metadata — no database connection required.
Written BEFORE model implementation per TDD workflow.
"""

import pytest
from sqlalchemy import inspect

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


class TestCommunityModel:
    """@brief Verify the communities table schema."""

    def test_table_exists(self):
        assert _get_table("communities") is not None

    def test_required_columns(self):
        cols = _get_columns("communities")
        assert {"id", "name", "created_at"}.issubset(cols)

    def test_primary_key(self):
        table = _get_table("communities")
        pk_names = [c.name for c in table.primary_key.columns]
        assert pk_names == ["id"]


class TestUserModel:
    """@brief Verify the users table schema."""

    def test_table_exists(self):
        assert _get_table("users") is not None

    def test_identity_columns(self):
        cols = _get_columns("users")
        expected = {
            "id", "community_id", "uri", "email", "username",
            "display_name", "password_hash", "role",
        }
        assert expected.issubset(cols)

    def test_profile_columns(self):
        cols = _get_columns("users")
        expected = {"avatar_url", "bio", "pronouns", "location", "website_url", "birthday"}
        assert expected.issubset(cols)

    def test_security_columns(self):
        cols = _get_columns("users")
        expected = {
            "is_active", "email_verified", "totp_secret",
            "totp_enabled", "oidc_sub",
        }
        assert expected.issubset(cols)

    def test_storage_columns(self):
        cols = _get_columns("users")
        assert {"storage_used", "storage_quota"}.issubset(cols)

    def test_soft_delete_column(self):
        cols = _get_columns("users")
        assert "deleted_at" in cols

    def test_timestamp_columns(self):
        cols = _get_columns("users")
        assert {"created_at", "updated_at", "last_seen_at"}.issubset(cols)

    def test_community_id_fk(self):
        table = _get_table("users")
        fk_targets = {
            str(fk.column) for col in table.columns for fk in col.foreign_keys
        }
        assert "communities.id" in fk_targets


class TestUserSettingsModel:
    """@brief Verify the user_settings table schema."""

    def test_table_exists(self):
        assert _get_table("user_settings") is not None

    def test_primary_key_is_user_id(self):
        table = _get_table("user_settings")
        pk_names = [c.name for c in table.primary_key.columns]
        assert pk_names == ["user_id"]

    def test_notification_columns_exist(self):
        cols = _get_columns("user_settings")
        assert "notif_mention_inapp" in cols
        assert "notif_dm_email" in cols

    def test_privacy_columns_exist(self):
        cols = _get_columns("user_settings")
        assert {"profile_visible_to", "show_online_status"}.issubset(cols)

    def test_appearance_columns(self):
        cols = _get_columns("user_settings")
        assert {"theme", "font_size", "compact_feed", "locale"}.issubset(cols)


class TestRefreshTokenModel:
    """@brief Verify the refresh_tokens table schema."""

    def test_table_exists(self):
        assert _get_table("refresh_tokens") is not None

    def test_required_columns(self):
        cols = _get_columns("refresh_tokens")
        expected = {
            "id", "user_id", "token_hash", "family_id",
            "expires_at", "revoked_at", "created_at",
        }
        assert expected.issubset(cols)


class TestUserBackupCodeModel:
    """@brief Verify the user_backup_codes table schema."""

    def test_table_exists(self):
        assert _get_table("user_backup_codes") is not None

    def test_required_columns(self):
        cols = _get_columns("user_backup_codes")
        assert {"id", "user_id", "code_hash", "used_at", "created_at"}.issubset(cols)


class TestInviteModel:
    """@brief Verify the invites table schema."""

    def test_table_exists(self):
        assert _get_table("invites") is not None

    def test_required_columns(self):
        cols = _get_columns("invites")
        expected = {
            "id", "community_id", "email", "role", "token_hash",
            "created_by", "used_by", "expires_at", "used_at", "created_at",
        }
        assert expected.issubset(cols)
