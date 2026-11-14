"""
@file test_provider_ping.py
@brief Unit tests for provider ``ping()`` (real network probe, mocked HTTP client).
"""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.ollama_provider import OllamaProvider
from app.services.ai.openai_provider import OpenAIProvider


def _client(fail: bool = False) -> AsyncMock:
    resp = MagicMock()
    if fail:
        req = httpx.Request("GET", "http://x")
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=req, response=httpx.Response(401, request=req)
        )
    client = AsyncMock()
    client.get.return_value = resp
    return client


def _providers(client: AsyncMock) -> list[tuple[object, str]]:
    return [
        (AnthropicProvider("k", client=client), "https://api.anthropic.com/v1/models"),
        (OpenAIProvider("k", client=client), "https://api.openai.com/v1/models"),
        (OllamaProvider("http://o:11434/", "m", client=client), "http://o:11434/api/tags"),
    ]


@pytest.mark.parametrize("idx", [0, 1, 2])
async def test_ping_hits_provider_endpoint(idx):
    client = _client()
    provider, url = _providers(client)[idx]
    await provider.ping()  # type: ignore[attr-defined]
    client.get.assert_awaited_once()
    assert client.get.await_args.args[0] == url


@pytest.mark.parametrize("idx", [0, 1])
async def test_ping_sends_api_key(idx):
    client = _client()
    provider, _ = _providers(client)[idx]
    await provider.ping()  # type: ignore[attr-defined]
    headers = client.get.await_args.kwargs["headers"]
    assert "k" in " ".join(headers.values())


@pytest.mark.parametrize("idx", [0, 1, 2])
async def test_ping_raises_on_http_error(idx):
    client = _client(fail=True)
    provider, _ = _providers(client)[idx]
    with pytest.raises(httpx.HTTPStatusError):
        await provider.ping()  # type: ignore[attr-defined]


@pytest.mark.parametrize("idx", [0, 1, 2])
async def test_ping_raises_when_unreachable(idx):
    client = AsyncMock()
    client.get.side_effect = httpx.ConnectError("down")
    provider, _ = _providers(client)[idx]
    with pytest.raises(httpx.ConnectError):
        await provider.ping()  # type: ignore[attr-defined]
