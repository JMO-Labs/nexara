"""
@file __init__.py
@brief AI provider abstraction (Anthropic, OpenAI, Ollama) and OCR pipeline.
"""

from app.services.ai.provider import (
    AIBudgetExhaustedError,
    AIError,
    AIProvider,
    AIProviderConfigError,
    create_provider,
    get_ai_provider,
)

__all__ = [
    "AIBudgetExhaustedError",
    "AIError",
    "AIProvider",
    "AIProviderConfigError",
    "create_provider",
    "get_ai_provider",
]
