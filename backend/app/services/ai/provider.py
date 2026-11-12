"""
@file provider.py
@brief Minimal AI provider protocol used by background pipelines.

No concrete provider ships yet; ``get_ai_provider`` returns None until one is
registered, which makes every AI feature degrade gracefully.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import structlog

from app.core.config import Settings

logger = structlog.get_logger(__name__)


class AIError(Exception):
    """@brief Generic AI provider failure."""


class AIBudgetExhaustedError(AIError):
    """@brief Raised when the AI usage budget is exhausted."""


@runtime_checkable
class AIProvider(Protocol):
    """@brief Interface for AI backends."""

    async def vision(self, image: bytes, prompt: str, *, max_tokens: int = 1000) -> str:
        """
        @brief Run a vision prompt against an image.
        @param image Raw image bytes.
        @param prompt Instruction text.
        @param max_tokens Output token cap.
        @return Model text output.
        @raises AIBudgetExhaustedError When budget is used up.
        @raises AIError On any other provider failure.
        """
        ...


_PROVIDERS: dict[str, type[AIProvider]] = {}
"""@brief Registry of provider name -> implementation class."""


def get_ai_provider(settings: Settings) -> AIProvider | None:
    """
    @brief Return the configured provider or None when AI is disabled.
    @param settings Application settings.
    @return Provider instance or None.
    """
    name = settings.AI_PROVIDER
    if not name:
        return None
    cls = _PROVIDERS.get(name)
    if cls is None:
        logger.warning("ai_provider_unknown", provider=name)
        return None
    return cls()
