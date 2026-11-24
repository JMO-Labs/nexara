"""
@file user.py
@brief User model with identity, profile, security, and storage fields.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

COMMUNITY_DEFAULT = "00000000-0000-0000-0000-000000000001"


class User(Base):
    """
    @brief Core user account with identity, profile, security, and quota fields.

    Soft-deleted via deleted_at. The active_users view filters these out.
    """

    __tablename__ = "users"

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
    uri: Mapped[str | None] = mapped_column(Text, unique=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    username: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="member")

    # Profile
    avatar_url: Mapped[str | None] = mapped_column(Text)
    bio: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    pronouns: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    website_url: Mapped[str | None] = mapped_column(Text)
    birthday: Mapped[date | None] = mapped_column(Date)
    banner_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media.id", ondelete="SET NULL", use_alter=True),
    )
    # Optional contact/about fields; who sees each is user_settings.field_visibility.
    phone: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    links: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB, nullable=False, server_default="[]", default=list
    )
    emergency_contact: Mapped[dict[str, str] | None] = mapped_column(JSONB)
    skills: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]", default=list
    )
    availability: Mapped[str | None] = mapped_column(Text)
    dietary: Mapped[str | None] = mapped_column(Text)

    # Security
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    # Set by an admin when the person has passed away (migration 0056).
    memorialized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    passed_on: Mapped[date | None] = mapped_column(Date)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    totp_secret: Mapped[str | None] = mapped_column(Text)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Fernet token of an enrollment-in-progress secret (promoted on confirm).
    totp_pending_secret: Mapped[str | None] = mapped_column(Text)
    two_factor_required_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    oidc_sub: Mapped[str | None] = mapped_column(Text, unique=True)

    # Bot
    is_bot: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    sassybot_opt_out: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # Storage
    storage_used: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    storage_quota: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default="10737418240",
    )

    # Full-text search
    search_fts = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', "
            "coalesce(display_name, '') || ' ' || "
            "coalesce(username, '') || ' ' || "
            "coalesce(bio, ''))",
            persisted=True,
        ),
    )

    # Timestamps
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tour_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str | None] = mapped_column(Text)  # IANA zone; None -> UTC

    __table_args__ = (
        Index("users_email_idx", "email"),
        Index("users_role_idx", "role"),
        Index("users_username_idx", "username"),
        Index("users_search_fts_idx", "search_fts", postgresql_using="gin"),
    )
