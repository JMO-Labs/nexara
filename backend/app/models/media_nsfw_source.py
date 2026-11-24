"""
@file media_nsfw_source.py
@brief A post or album whose moderator/admin NSFW flag reached a photo
       (migration 0074). The photo stays NSFW, locked at ``level``, until that
       container is unflagged, even after it is moved out.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MediaNsfwSource(Base):
    """@brief Row in media_nsfw_sources."""

    __tablename__ = "media_nsfw_sources"

    media_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), primary_key=True
    )
    source_kind: Mapped[str] = mapped_column(Text, primary_key=True)  # 'post' | 'gallery'
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[str] = mapped_column(Text, nullable=False)  # 'admin' | 'moderator'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
