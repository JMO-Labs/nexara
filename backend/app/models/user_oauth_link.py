"""
@file user_oauth_link.py
@brief Links a User to an OAuth provider identity (sub claim).

Stores the provider-specific subject identifier and cached claims for
account linking and SSO login.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class UserOAuthLink(Base, UUIDPrimaryKeyMixin):
    """
    @brief Links a user account to an OAuth provider identity.

    One user can have multiple links (e.g. Google + GitHub). The combination
    (provider_id, sub) is unique.
    """

    __tablename__ = "user_oauth_links"
    __table_args__ = (UniqueConstraint("provider_id", "sub", name="uq_oauth_link_provider_sub"),)

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
    raw_claims: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
