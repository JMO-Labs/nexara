"""
@file chat.py
@brief ChatMessage and DirectMessageParticipant models.

Phase 2 Group 2 augmentations:
  * ``ChatMessage`` now has a nullable ``channel_id`` foreign key linking
    each persisted message to a :class:`ChatChannel`.  A composite
    ``(channel_id, created_at DESC)`` index backs the paginated history
    query used by the chat service.
  * ``DirectMessageParticipant`` is a small join table mapping a
    ``direct``-type ``ChatChannel`` to its two participating users.  The
    canonical lookup (``get_or_create_dm``) sorts the two user UUIDs and
    intersects the participants to find any existing DM channel.
"""

import uuid
from datetime import datetime

from sqlalchemy import Computed, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


class ChatMessage(Base):
    """@brief Real-time chat messages persisted to Postgres after Valkey delivery."""

    __tablename__ = "chat_messages"

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
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_channels.id", ondelete="CASCADE"),
        nullable=True,
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_fts = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', content)", persisted=True),
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("chat_messages_created_idx", created_at.desc()),
        Index("chat_messages_fts_idx", "content_fts", postgresql_using="gin"),
        Index("chat_messages_channel_idx", "channel_id", created_at.desc()),
    )


class DirectMessageParticipant(Base):
    """
    @brief Join table linking a DM :class:`ChatChannel` to its participants.

    A DM channel is created on first message between two users; two rows
    are inserted (one per participant) sharing the same ``channel_id``.
    The ``(channel_id, user_id)`` composite primary key guarantees a
    user cannot be associated with the same DM twice.
    """

    __tablename__ = "direct_message_participants"

    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_channels.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("dm_participants_user_idx", "user_id"),)
