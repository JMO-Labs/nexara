"""
@file test_oauth_provider.py
@brief Unit tests for OAuthProvider model structure.
"""

import app.models  # noqa: F401 — register all models with Base.metadata
from app.models.oauth_provider import OAuthProvider


class TestOAuthProviderModel:
    """@brief Verify the OAuthProvider model schema."""

    def test_tablename(self):
        """OAuthProvider table name should be oauth_providers."""
        assert OAuthProvider.__tablename__ == "oauth_providers"

    def test_has_required_columns(self):
        """OAuthProvider should have all required columns."""
        cols = {c.name for c in OAuthProvider.__table__.columns}
        required = {
            "id",
            "community_id",
            "slug",
            "display_name",
            "provider_type",
            "client_id",
            "client_secret_encrypted",
            "scopes",
            "issuer",
            "authorization_endpoint",
            "token_endpoint",
            "userinfo_endpoint",
            "jwks_uri",
            "end_session_endpoint",
            "group_mappings",
            "default_role",
            "group_claim",
            "avatar_claim",
            "sub_claim",
            "email_claim",
            "name_claim",
            "icon_url",
            "enabled",
            "auto_create_users",
            "seeded_from_env",
            "created_at",
            "updated_at",
        }
        assert required.issubset(cols)
