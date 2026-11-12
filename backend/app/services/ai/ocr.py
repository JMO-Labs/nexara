"""
@file ocr.py
@brief OCR core logic: extract text from an image and persist it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from app.core.metrics import ocr_processed_total
from app.repositories.media_ai_repo import MediaAIRepository
from app.repositories.media_repo import MediaRepository
from app.services.ai.provider import AIBudgetExhaustedError, AIError, AIProvider
from app.services.storage.base import StorageBackend

logger = structlog.get_logger(__name__)

OCR_PROMPT = "Extract all visible text. Return only text, one line per element."
OCR_MAX_TOKENS = 2000


async def run_ocr(
    media_id: uuid.UUID,
    community_id: uuid.UUID,
    *,
    media_repo: MediaRepository,
    ai_repo: MediaAIRepository,
    storage: StorageBackend,
    provider: AIProvider | None,
) -> str:
    """
    @brief OCR one media item; never raises for AI problems.
    @param media_id Media UUID.
    @param community_id Tenant scope.
    @return One of processed | skipped | budget_exhausted | error.
    """

    def _done(status: str) -> str:
        ocr_processed_total.labels(status=status).inc()
        return status

    if provider is None:
        return _done("skipped")
    media = await media_repo.get(media_id)
    if media is None or not media.content_type.startswith("image/"):
        return _done("skipped")
    try:
        image = await storage.get(media.storage_key)
        text = await provider.vision(image, OCR_PROMPT, max_tokens=OCR_MAX_TOKENS)
    except AIBudgetExhaustedError:
        logger.info("ocr_budget_exhausted", media_id=str(media_id))
        return _done("budget_exhausted")
    except Exception as exc:  # AIError or storage failure; OCR is best-effort
        logger.warning("ocr_failed", media_id=str(media_id), error=str(exc))
        return _done("error")
    await ai_repo.create(
        media_id,
        community_id=community_id,
        ocr_text=text.strip(),
        processed_at=datetime.now(UTC),
    )
    return _done("processed")


__all__ = ["AIError", "OCR_PROMPT", "run_ocr"]
