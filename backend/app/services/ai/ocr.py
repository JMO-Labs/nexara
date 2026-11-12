"""
@file ocr.py
@brief OCR core logic: extract text from an image and persist it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from app.core.metrics import ai_budget_exceeded_total, ocr_processed_total
from app.repositories.media_ai_repo import MediaAIRepository
from app.repositories.media_repo import MediaRepository
from app.services.ai.budget_service import BudgetService
from app.services.ai.provider import AIBudgetExhaustedError, AIError, AIProvider
from app.services.storage.base import StorageBackend

logger = structlog.get_logger(__name__)

OCR_PROMPT = "Extract all visible text. Return only text, one line per element."
OCR_MAX_TOKENS = 2000
#: Pre-call estimate (cents) used for the budget gate.
OCR_ESTIMATED_CENTS = 1.0


async def run_ocr(
    media_id: uuid.UUID,
    community_id: uuid.UUID,
    *,
    media_repo: MediaRepository,
    ai_repo: MediaAIRepository,
    storage: StorageBackend,
    provider: AIProvider | None,
    budget: BudgetService | None = None,
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
    media = await media_repo.get_by_id(media_id, community_id)
    if media is None or not media.content_type.startswith("image/"):
        return _done("skipped")
    if await ai_repo.get_by_media_id(media_id) is not None:
        return _done("skipped")  # retry/re-enqueue: already processed
    if budget is not None and not await budget.check_budget(OCR_ESTIMATED_CENTS):
        ai_budget_exceeded_total.labels(community_id=str(community_id)).inc()
        return _done("budget_exhausted")
    try:
        image = await storage.get(media.storage_key)
        text, cost, _tokens = await provider.vision(image, OCR_PROMPT, max_tokens=OCR_MAX_TOKENS)
        if budget is not None:
            await budget.record_usage(
                cost, "ocr", provider=type(provider).__name__.removesuffix("Provider").lower()
            )
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
