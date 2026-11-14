"""
@file webhook.py
@brief Outbound webhook subscriptions (per-user and per-community).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WebhookSubscription(Base):
    """
    @brief A webhook target; ``user_id`` NULL means community-level (admin owned).

    ``type_keys`` empty means the subscription receives every notification type.
    """

    __tablename__ = "webhook_subscriptions"
    __table_args__ = (
        Index("webhook_subs_community_idx", "community_id", postgresql_where=text("enabled")),
        Index(
            "webhook_subs_user_idx",
            "user_id",
            postgresql_where=text("enabled AND user_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    secret: Mapped[str] = mapped_column(Text, nullable=False)
    type_keys: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
