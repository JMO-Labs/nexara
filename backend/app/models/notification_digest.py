"""
@file notification_digest.py
@brief Queue of notifications awaiting inclusion in an email digest.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationDigestQueue(Base):
    """@brief One pending notification queued for a (user, type) digest."""

    __tablename__ = "notification_digest_queue"
    __table_args__ = (Index("digest_queue_drain_idx", "user_id", "type_key", "enqueued_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    type_key: Mapped[str] = mapped_column(Text, nullable=False)
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notifications.id", ondelete="CASCADE"), primary_key=True
    )
    enqueued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
