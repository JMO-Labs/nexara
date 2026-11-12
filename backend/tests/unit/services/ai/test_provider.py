"""
@file test_provider.py
@brief Unit tests for the AI provider protocol, implementations and factory.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.ollama_provider import OllamaProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.provider import (
    AIProvider,
    AIProviderConfigError,
    create_provider,
)


def _settings(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


def _client(payload: dict) -> AsyncMock:
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    client = AsyncMock()
    client.post.return_value = resp
    return client


class TestFactory:
    def test_unconfigured_returns_none(self):
        assert create_provider(_settings(AI_PROVIDER="")) is None

    def test_unknown_provider_returns_none(self):
        assert create_provider(_settings(AI_PROVIDER="bogus")) is None

    @pytest.mark.parametrize(
        ("kw", "cls"),
        [
            ({"AI_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "k"}, AnthropicProvider),
            ({"AI_PROVIDER": "openai", "OPENAI_API_KEY": "k"}, OpenAIProvider),
            ({"AI_PROVIDER": "ollama", "OLLAMA_BASE_URL": "http://o:11434"}, OllamaProvider),
        ],
    )
    def test_returns_correct_provider(self, kw, cls):
        p = create_provider(_settings(**kw))
        assert isinstance(p, cls)
        assert isinstance(p, AIProvider)

    @pytest.mark.parametrize("name", ["anthropic", "openai", "ollama"])
    def test_missing_required_env_raises(self, name):
        with pytest.raises(AIProviderConfigError):
            create_provider(_settings(AI_PROVIDER=name, OLLAMA_BASE_URL=""))

    def test_name_is_case_insensitive(self):
        p = create_provider(_settings(AI_PROVIDER="OpenAI", OPENAI_API_KEY="k"))
        assert isinstance(p, OpenAIProvider)


class TestAnthropic:
    async def test_complete_returns_text_cost_tokens(self):
        client = _client(
            {
                "content": [{"type": "text", "text": "hi"}],
                "usage": {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
            }
        )
        p = AnthropicProvider(api_key="k", client=client)
        text, cost, tokens = await p.complete("p", 10, 0.5)
        assert text == "hi"
        assert tokens == 2_000_000
        assert cost == pytest.approx(150.0)  # 25c in + 125c out
        assert client.post.call_args.kwargs["headers"]["x-api-key"] == "k"

    async def test_vision_uses_sonnet(self):
        client = _client(
            {
                "content": [{"type": "text", "text": "cat"}],
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }
        )
        p = AnthropicProvider(api_key="k", client=client)
        text, _, tokens = await p.vision(b"\x89PNG", "what", 50)
        assert text == "cat"
        assert tokens == 15
        assert "sonnet" in client.post.call_args.kwargs["json"]["model"]

    async def test_count_tokens_estimates(self):
        p = AnthropicProvider(api_key="k", client=AsyncMock())
        n, cost, tokens = await p.count_tokens("a" * 40)
        assert n == tokens == 10
        assert cost == 0.0

    async def test_embed_unsupported(self):
        p = AnthropicProvider(api_key="k", client=AsyncMock())
        with pytest.raises(NotImplementedError):
            await p.embed("x")


class TestOpenAI:
    async def test_complete(self):
        client = _client(
            {
                "choices": [{"message": {"content": "yo"}}],
                "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000},
            }
        )
        p = OpenAIProvider(api_key="k", client=client)
        text, cost, tokens = await p.complete("p", 10, 0.2)
        assert (text, tokens) == ("yo", 2_000_000)
        assert cost == pytest.approx(75.0)  # 15c in + 60c out

    async def test_vision_uses_gpt4o(self):
        client = _client(
            {
                "choices": [{"message": {"content": "dog"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10},
            }
        )
        p = OpenAIProvider(api_key="k", client=client)
        text, _, tokens = await p.vision(b"img", "what", 20)
        assert (text, tokens) == ("dog", 110)
        assert client.post.call_args.kwargs["json"]["model"] == "gpt-4o"

    async def test_embed(self):
        client = _client({"data": [{"embedding": [0.1, 0.2]}], "usage": {"prompt_tokens": 3}})
        p = OpenAIProvider(api_key="k", client=client)
        vec, _, tokens = await p.embed("x")
        assert vec == [0.1, 0.2]
        assert tokens == 3

    async def test_count_tokens(self):
        p = OpenAIProvider(api_key="k", client=AsyncMock())
        n, _, tokens = await p.count_tokens("abcd" * 5)
        assert n == tokens == 5


class TestOllama:
    async def test_complete_is_free(self):
        client = _client({"response": "local", "prompt_eval_count": 4, "eval_count": 6})
        p = OllamaProvider(base_url="http://o:11434/", model="mistral", client=client)
        text, cost, tokens = await p.complete("p", 10, 0.1)
        assert (text, cost, tokens) == ("local", 0.0, 10)
        assert client.post.call_args.args[0] == "http://o:11434/api/generate"
        assert client.post.call_args.kwargs["json"]["model"] == "mistral"

    async def test_vision_sends_base64_image(self):
        client = _client({"response": "v", "prompt_eval_count": 1, "eval_count": 1})
        p = OllamaProvider(base_url="http://o", model="llava", client=client)
        await p.vision(b"abc", "q", 5)
        assert client.post.call_args.kwargs["json"]["images"] == ["YWJj"]

    async def test_embed(self):
        client = _client({"embedding": [1.0, 2.0]})
        p = OllamaProvider(base_url="http://o", model="m", client=client)
        vec, cost, tokens = await p.embed("hello")
        assert vec == [1.0, 2.0]
        assert cost == 0.0
        assert tokens >= 1
