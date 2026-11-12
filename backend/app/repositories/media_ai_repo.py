"""
@file media_ai_repo.py
@brief Repository for media_ai_metadata (OCR text and FTS).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from app.models.media_ai import MediaAIMetadata
from app.repositories.base import BaseRepository


class MediaAIRepository(BaseRepository[MediaAIMetadata]):
    """@brief CRUD + full-text search over OCR text."""

    model = MediaAIMetadata

    async def get_by_media_id(self, media_id: uuid.UUID) -> MediaAIMetadata | None:
        """@brief Fetch metadata for a media item or None."""
        res = await self._session.execute(
            select(MediaAIMetadata).where(MediaAIMetadata.media_id == media_id)
        )
        return res.scalar_one_or_none()

    async def create(  # type: ignore[override]
        self,
        media_id: uuid.UUID,
        *,
        community_id: uuid.UUID,
        ocr_text: str | None = None,
        description: str | None = None,
        tags: Any | None = None,
        processed_at: datetime | None = None,
    ) -> MediaAIMetadata:
        """@brief Insert a metadata row."""
        row = MediaAIMetadata(
            media_id=media_id,
            community_id=community_id,
            ocr_text=ocr_text,
            description=description,
            tags=tags,
            processed_at=processed_at,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def search_by_fts(
        self, query: str, community_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> list[MediaAIMetadata]:
        """@brief Rows whose OCR text matches ``query``, best rank first."""
        tsq = func.websearch_to_tsquery("english", query)
        stmt = (
            select(MediaAIMetadata)
            .where(
                MediaAIMetadata.community_id == community_id,
                MediaAIMetadata.ocr_fts.op("@@")(tsq),
            )
            .order_by(func.ts_rank(MediaAIMetadata.ocr_fts, tsq).desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self._session.execute(stmt)
        return list(res.scalars().all())
