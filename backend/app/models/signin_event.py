"""
@file signin_event.py
@brief SigninEvent model: one row per sign-in attempt (success or failure).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

SIGNIN_METHODS = ("password", "totp", "recovery", "passkey", "magic_link", "sso")
"""@brief Allowed ``signin_events.method`` values."""


class SigninEvent(Base):
    """
    @brief Sign-in attempt record. Never stores the attempted password.

    ``user_id`` is NULL for unknown-email attempts. Purged after 90 days.
    """

    __tablename__ = "signin_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("communities.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    email_tried: Mapped[str | None] = mapped_column(Text)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    device: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "method IN ('password','totp','recovery','passkey','magic_link','sso')",
            name="ck_signin_events_method",
        ),
        Index("ix_signin_events_community_created", "community_id", created_at.desc()),
        Index("ix_signin_events_ip_created", "ip", "created_at"),
    )
