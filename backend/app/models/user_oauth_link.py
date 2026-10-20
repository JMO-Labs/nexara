"""
@file user_oauth_link.py
@brief Links a user account to their OAuth provider identity.

Stores the provider's ``sub`` claim and optional profile data.
Unique on (provider_id, sub) to prevent duplicate links.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserOAuthLink(Base):
    """
    @brief Links a user account to an OAuth provider identity.

    Tracks the provider's subject claim, email, avatar, and raw claims.
    """

    __tablename__ = "user_oauth_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("oauth_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    sub: Mapped[str] = mapped_column(String(256), nullable=False)
    email_from_provider: Mapped[str | None] = mapped_column(String(256))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    raw_claims: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("provider_id", "sub", name="uq_oauth_link_provider_sub"),
        Index("user_oauth_links_user_idx", "user_id"),
        Index("user_oauth_links_provider_idx", "provider_id"),
    )
