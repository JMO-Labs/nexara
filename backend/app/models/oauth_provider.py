"""
@file oauth_provider.py
@brief OAuth/OIDC provider configuration model.

Stores per-community OAuth2/OIDC provider settings including client credentials
(encrypted), OIDC endpoints, claim mappings, and group-to-role mappings.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


class OAuthProvider(Base):
    """
    @brief OAuth/OIDC provider configuration per community.

    Stores client credentials (encrypted), endpoints, and claim mappings.
    Soft-deleted via deleted_at.
    """

    __tablename__ = "oauth_providers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(Text)
    provider_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="oidc")
    issuer: Mapped[str | None] = mapped_column(Text)
    client_id: Mapped[str] = mapped_column(String(256), nullable=False)
    client_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        server_default="openid profile email groups",
    )
    authorization_endpoint: Mapped[str | None] = mapped_column(Text)
    token_endpoint: Mapped[str | None] = mapped_column(Text)
    userinfo_endpoint: Mapped[str | None] = mapped_column(Text)
    jwks_uri: Mapped[str | None] = mapped_column(Text)
    end_session_endpoint: Mapped[str | None] = mapped_column(Text)
    group_mappings: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    default_role: Mapped[str] = mapped_column(String(32), nullable=False, server_default="member")
    group_claim: Mapped[str] = mapped_column(String(64), nullable=False, server_default="groups")
    avatar_claim: Mapped[str] = mapped_column(String(64), nullable=False, server_default="picture")
    sub_claim: Mapped[str] = mapped_column(String(64), nullable=False, server_default="sub")
    email_claim: Mapped[str] = mapped_column(String(64), nullable=False, server_default="email")
    name_claim: Mapped[str] = mapped_column(String(64), nullable=False, server_default="name")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    auto_create_users: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    seeded_from_env: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("community_id", "slug", name="uq_oauth_provider_community_slug"),
    )
