"""
@file chat_read.py
@brief ChatRead model — per-user, per-channel read marker for chat unread counts.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


class ChatRead(Base):
    """
    @brief Records when a user last read a chat channel.

    Composite primary key (user_id, channel_id); upserted, never moves backwards.
    """

    __tablename__ = "chat_reads"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_channels.id", ondelete="CASCADE"),
        primary_key=True,
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_chat_reads_user_id", "user_id"),)
