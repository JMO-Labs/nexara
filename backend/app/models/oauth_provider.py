"""
@file oauth_provider.py
@brief OAuth2/OIDC provider configuration model.

Stores per-community OAuth provider settings (client credentials, endpoints,
claim mappings) for multi-provider SSO.
"""

import uuid

from sqlalchemy import (
    Boolean,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OAuthProvider(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    @brief OAuth2/OIDC provider configuration for a community.

    Each community can have multiple providers (e.g. Google, Azure AD).
    Identified by (community_id, slug) uniquely.
    """

    __tablename__ = "oauth_providers"
    __table_args__ = (
        UniqueConstraint("community_id", "slug", name="uq_oauth_provider_community_slug"),
    )

    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(Text)
    provider_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="oidc")
    issuer: Mapped[str | None] = mapped_column(Text)
    client_id: Mapped[str] = mapped_column(String(256), nullable=False)
    client_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str] = mapped_column(
        String(512), nullable=False, server_default="openid profile email groups"
    )
    authorization_endpoint: Mapped[str | None] = mapped_column(Text)
    token_endpoint: Mapped[str | None] = mapped_column(Text)
    userinfo_endpoint: Mapped[str | None] = mapped_column(Text)
    jwks_uri: Mapped[str | None] = mapped_column(Text)
    end_session_endpoint: Mapped[str | None] = mapped_column(Text)
    group_mappings: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'")
    )
    default_role: Mapped[str] = mapped_column(String(32), server_default="member")
    group_claim: Mapped[str] = mapped_column(String(64), server_default="groups")
    avatar_claim: Mapped[str] = mapped_column(String(64), server_default="picture")
    sub_claim: Mapped[str] = mapped_column(String(64), server_default="sub")
    email_claim: Mapped[str] = mapped_column(String(64), server_default="email")
    name_claim: Mapped[str] = mapped_column(String(64), server_default="name")
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="true")
    auto_create_users: Mapped[bool] = mapped_column(Boolean, server_default="true")
    seeded_from_env: Mapped[bool] = mapped_column(Boolean, server_default="false")
