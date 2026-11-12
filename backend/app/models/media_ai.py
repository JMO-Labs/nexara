"""
@file media_ai.py
@brief AI-derived metadata (OCR text, description, tags) for media.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Computed, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MediaAIMetadata(Base):
    """@brief One row per media item; ``ocr_fts`` is a generated column."""

    __tablename__ = "media_ai_metadata"

    media_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), primary_key=True
    )
    ocr_text: Mapped[str | None] = mapped_column(Text)
    ocr_fts: Mapped[Any] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', ocr_text)", persisted=True)
    )
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[Any | None] = mapped_column(JSONB)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("communities.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("idx_media_ai_metadata_ocr_fts", "ocr_fts", postgresql_using="gin"),)
