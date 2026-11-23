"""
@file newsletter.py
@brief Admin pin/hide overrides for the monthly newsletter (migration 0065).
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


class NewsletterOverride(Base):
    """@brief Row in newsletter_overrides: one admin pin or hide for a post in a month."""

    __tablename__ = "newsletter_overrides"
    __table_args__ = (
        CheckConstraint("action IN ('pin','hide')", name="newsletter_overrides_action_ck"),
    )

    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        primary_key=True,
        server_default=COMMUNITY_DEFAULT,
    )
    month: Mapped[str] = mapped_column(Text, primary_key=True)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
