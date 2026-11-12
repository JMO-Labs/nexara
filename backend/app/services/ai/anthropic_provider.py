"""
@file anthropic_provider.py
@brief Anthropic Claude provider (REST via httpx; no SDK dependency).
"""

from __future__ import annotations

import base64

import httpx

from app.services.ai.provider import (
    AIProvider,
    CountResult,
    EmbedResult,
    TextResult,
    cost_cents,
    estimate_tokens,
)

_URL = "https://api.anthropic.com/v1/messages"
TEXT_MODEL = "claude-3-haiku-20240307"
VISION_MODEL = "claude-3-sonnet-20240229"
#: model -> (USD/1M input, USD/1M output)
PRICING = {TEXT_MODEL: (0.25, 1.25), VISION_MODEL: (3.0, 15.0)}


class AnthropicProvider(AIProvider):
    """@brief Claude haiku for text, sonnet for vision. Embeddings unsupported."""

    def __init__(
        self, api_key: str, client: httpx.AsyncClient | None = None, timeout: float = 60.0
    ) -> None:
        self._key = api_key
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def _call(
        self, model: str, content: object, max_tokens: int, temp: float | None
    ) -> TextResult:
        body: dict[str, object] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": content}],
        }
        if temp is not None:
            body["temperature"] = temp
        resp = await self._client.post(
            _URL,
            headers={
                "x-api-key": self._key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        tin, tout = data["usage"]["input_tokens"], data["usage"]["output_tokens"]
        rin, rout = PRICING[model]
        return text, cost_cents(tin, tout, rin, rout), tin + tout

    async def complete(self, prompt: str, max_tokens: int, temperature: float) -> TextResult:
        return await self._call(TEXT_MODEL, prompt, max_tokens, temperature)

    async def vision(self, image_bytes: bytes, prompt: str, max_tokens: int) -> TextResult:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": _sniff(image_bytes),
                    "data": base64.b64encode(image_bytes).decode(),
                },
            },
            {"type": "text", "text": prompt},
        ]
        return await self._call(VISION_MODEL, content, max_tokens, None)

    async def embed(self, text: str) -> EmbedResult:
        raise NotImplementedError("Anthropic does not offer embeddings")

    async def count_tokens(self, text: str) -> CountResult:
        n = estimate_tokens(text)
        return n, 0.0, n


def _sniff(data: bytes) -> str:
    """@brief Guess image media type from magic bytes (default PNG)."""
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data.startswith(b"GIF8"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"
