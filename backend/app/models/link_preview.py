"""
@file link_preview.py
@brief LinkPreview, PostLinkPreview, and ChatMessageLinkPreview models.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, SmallInteger, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LinkPreview(Base):
    """@brief Cached OpenGraph metadata for URLs shared in posts and messages."""

    __tablename__ = "link_previews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(),
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    url_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    site_name: Mapped[str | None] = mapped_column(Text)
    provider_type: Mapped[str | None] = mapped_column(Text)
    provider_id: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetch_error: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    __table_args__ = (
        Index("link_previews_url_hash_idx", "url_hash"),
        Index("link_previews_expires_idx", "expires_at"),
    )


class PostLinkPreview(Base):
    """@brief Junction linking posts to their link previews."""

    __tablename__ = "post_link_previews"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    preview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")


class ChatMessageLinkPreview(Base):
    """@brief Junction linking chat messages to their link previews."""

    __tablename__ = "chat_message_link_previews"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    preview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
