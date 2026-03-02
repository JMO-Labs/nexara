"""
@file test_user_oauth_link.py
@brief Unit tests for UserOAuthLink model structure.
"""

import app.models  # noqa: F401 — register all models with Base.metadata
from app.models.user_oauth_link import UserOAuthLink


class TestUserOAuthLinkModel:
    """@brief Verify the UserOAuthLink model schema."""

    def test_tablename(self):
        """UserOAuthLink table name should be user_oauth_links."""
        assert UserOAuthLink.__tablename__ == "user_oauth_links"

    def test_has_required_columns(self):
        """UserOAuthLink should have all required columns."""
        cols = {c.name for c in UserOAuthLink.__table__.columns}
        required = {
            "id",
            "user_id",
            "provider_id",
            "sub",
            "email_from_provider",
            "avatar_url",
            "raw_claims",
            "linked_at",
        }
        assert required.issubset(cols)
