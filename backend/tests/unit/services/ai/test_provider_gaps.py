"""
@file test_provider_gaps.py
@brief Covers image sniffing, Ollama token counting and misconfigured-provider fallback.
"""

import pytest

from app.core.config import Settings
from app.services.ai.anthropic_provider import _sniff
from app.services.ai.ollama_provider import OllamaProvider
from app.services.ai.provider import get_ai_provider


class TestSniff:
    @pytest.mark.parametrize(
        ("data", "mime"),
        [
            (b"\xff\xd8\xff\xe0", "image/jpeg"),
            (b"GIF89a", "image/gif"),
            (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "image/webp"),
            (b"RIFF\x00\x00\x00\x00WAVE", "image/png"),
            (b"\x89PNG", "image/png"),
        ],
    )
    def test_sniff(self, data, mime):
        assert _sniff(data) == mime


class TestOllamaCount:
    async def test_count_tokens_is_free_estimate(self):
        p = OllamaProvider(base_url="http://o", model="m")
        n, cost, tokens = await p.count_tokens("a" * 40)
        assert n == tokens == 10
        assert cost == 0.0


class TestGetAIProvider:
    def test_misconfigured_returns_none(self):
        s = Settings(_env_file=None, AI_PROVIDER="anthropic", ANTHROPIC_API_KEY="")
        assert get_ai_provider(s) is None

    def test_configured_returns_provider(self):
        s = Settings(_env_file=None, AI_PROVIDER="openai", OPENAI_API_KEY="k")
        assert get_ai_provider(s) is not None
