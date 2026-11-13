"""
@file provider.py
@brief AIProvider abstract interface and provider factory.

Every method returns ``(result, cost_cents, token_count)`` for metering.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from app.core.config import Settings

#: (text, cost_cents, token_count)
TextResult = tuple[str, float, int]
#: (vector, cost_cents, token_count)
EmbedResult = tuple[list[float], float, int]
#: (token_count, cost_cents, token_count)
CountResult = tuple[int, float, int]

logger = structlog.get_logger(__name__)

_PER_MILLION = 1_000_000


class AIError(Exception):
    """@brief Generic AI provider failure."""


class AIBudgetExhaustedError(AIError):
    """@brief Raised when the AI usage budget is exhausted."""


class AIProviderConfigError(ValueError):
    """@brief Raised when a selected provider lacks required configuration."""


def cost_cents(in_tokens: int, out_tokens: int, in_rate: float, out_rate: float) -> float:
    """
    @brief Cost in cents from token counts and USD-per-1M-token rates.
    @param in_tokens Prompt tokens.
    @param out_tokens Completion tokens.
    @param in_rate USD per 1M input tokens.
    @param out_rate USD per 1M output tokens.
    @return Cost in cents.
    """
    return (in_tokens * in_rate + out_tokens * out_rate) / _PER_MILLION * 100


def estimate_tokens(text: str) -> int:
    """@brief Rough token estimate (~4 chars per token), minimum 1 if non-empty."""
    return max(1, len(text) // 4) if text else 0


class AIProvider(ABC):
    """@brief Abstract AI provider; all methods are async and return metering tuples."""

    @abstractmethod
    async def complete(self, prompt: str, max_tokens: int, temperature: float) -> TextResult:
        """@brief Generate text. @return (text, cost_cents, token_count)."""

    @abstractmethod
    async def vision(self, image_bytes: bytes, prompt: str, max_tokens: int) -> TextResult:
        """@brief Analyse an image. @return (text, cost_cents, token_count)."""

    @abstractmethod
    async def embed(self, text: str) -> EmbedResult:
        """@brief Embed text. @return (vector, cost_cents, token_count)."""

    @abstractmethod
    async def ping(self) -> None:
        """@brief Cheap network probe; raises if the provider is unreachable or rejects auth."""

    @abstractmethod
    async def count_tokens(self, text: str) -> CountResult:
        """@brief Count tokens. @return (count, cost_cents, token_count)."""


def create_provider(settings: Settings) -> AIProvider | None:
    """
    @brief Build the provider selected by ``AI_PROVIDER``.
    @param settings Application settings.
    @return Provider, or None when AI is unset/unknown (graceful degradation).
    @throws AIProviderConfigError if the selected provider lacks required env vars.
    """
    name = settings.AI_PROVIDER.strip().lower()
    timeout = settings.AI_HTTP_TIMEOUT
    if name == "anthropic":
        from app.services.ai.anthropic_provider import AnthropicProvider

        if not settings.ANTHROPIC_API_KEY:
            raise AIProviderConfigError("ANTHROPIC_API_KEY is required")
        return AnthropicProvider(settings.ANTHROPIC_API_KEY, timeout=timeout)
    if name == "openai":
        from app.services.ai.openai_provider import OpenAIProvider

        if not settings.OPENAI_API_KEY:
            raise AIProviderConfigError("OPENAI_API_KEY is required")
        return OpenAIProvider(settings.OPENAI_API_KEY, timeout=timeout)
    if name == "ollama":
        from app.services.ai.ollama_provider import OllamaProvider

        if not settings.OLLAMA_BASE_URL:
            raise AIProviderConfigError("OLLAMA_BASE_URL is required")
        return OllamaProvider(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL, timeout=timeout)
    return None


def get_ai_provider(settings: Settings) -> AIProvider | None:
    """
    @brief Return the configured provider or None when AI is disabled/misconfigured.
    @param settings Application settings.
    @return Provider instance or None.
    """
    try:
        return create_provider(settings)
    except AIProviderConfigError as exc:
        logger.warning("ai_provider_misconfigured", error=str(exc))
        return None
