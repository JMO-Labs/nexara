"""
@file community.py
@brief Community model — single-row table for multi-tenancy preparation.

Every community-scoped table references communities.id via community_id FK.
In v1 there is exactly one community per instance.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Community(Base):
    """
    @brief The root entity for multi-tenancy preparation.

    A single row is seeded on first migration. All community-scoped tables
    carry a community_id FK defaulting to the sentinel UUID.
    """

    __tablename__ = "communities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="Nexara",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    sassybot_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    sassybot_sass_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="2")
    sassybot_probability: Mapped[int] = mapped_column(Integer, nullable=False, server_default="15")
    sassybot_invoke_only: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    # Amazon Creators API (wishlist prices); secret is Fernet-encrypted.
    amazon_client_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    amazon_client_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    amazon_partner_tag: Mapped[str | None] = mapped_column(Text, nullable=True)
    amazon_marketplace: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Reply by email (IMAP polling); password is Fernet-encrypted, write-only.
    inbound_imap_host: Mapped[str | None] = mapped_column(Text, nullable=True)
    inbound_imap_port: Mapped[int] = mapped_column(Integer, nullable=False, server_default="993")
    inbound_imap_user: Mapped[str | None] = mapped_column(Text, nullable=True)
    inbound_imap_password: Mapped[str | None] = mapped_column(Text, nullable=True)
    inbound_reply_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Name the receiving server uses in Authentication-Results (e.g. mx.google.com).
    inbound_authserv_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    # SMTP (overrides env SMTP_*); password / google_refresh are Fernet-encrypted.
    # 2FA policy: off | admins | everyone (migration 0070).
    require_2fa: Mapped[str] = mapped_column(Text, nullable=False, server_default="off")
    # Members may add Apprise URLs that resolve to private/loopback addresses.
    apprise_allow_local: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    smtp_host: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smtp_security: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_user: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_password: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_from: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_from_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_auth: Mapped[str] = mapped_column(Text, nullable=False, server_default="password")
    smtp_google_refresh: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_google_client_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_google_client_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_last_ok_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    smtp_last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_retention_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="365")
    # Per-community feature flags (see app.core.features); unset keys use defaults.
    features: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    currency: Mapped[str] = mapped_column(Text, nullable=False, server_default="USD")
