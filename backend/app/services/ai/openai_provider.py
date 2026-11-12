"""
@file openai_provider.py
@brief OpenAI provider (REST via httpx; no SDK dependency).
"""

from __future__ import annotations

import base64

import httpx

from app.services.ai.anthropic_provider import _sniff
from app.services.ai.provider import (
    AIProvider,
    CountResult,
    EmbedResult,
    TextResult,
    cost_cents,
    estimate_tokens,
)

_BASE = "https://api.openai.com/v1"
TEXT_MODEL = "gpt-4o-mini"
VISION_MODEL = "gpt-4o"
EMBED_MODEL = "text-embedding-3-small"
#: model -> (USD/1M input, USD/1M output)
PRICING = {TEXT_MODEL: (0.15, 0.60), VISION_MODEL: (2.50, 10.0), EMBED_MODEL: (0.02, 0.0)}


class OpenAIProvider(AIProvider):
    """@brief gpt-4o-mini for text, gpt-4o for vision, text-embedding-3-small."""

    def __init__(
        self, api_key: str, client: httpx.AsyncClient | None = None, timeout: float = 60.0
    ) -> None:
        self._key = api_key
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def _post(self, path: str, body: dict[str, object]) -> dict:
        resp = await self._client.post(
            f"{_BASE}/{path}", headers={"Authorization": f"Bearer {self._key}"}, json=body
        )
        resp.raise_for_status()
        return resp.json()

    async def _chat(
        self, model: str, content: object, max_tokens: int, temp: float | None
    ) -> TextResult:
        body: dict[str, object] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": content}],
        }
        if temp is not None:
            body["temperature"] = temp
        data = await self._post("chat/completions", body)
        usage = data["usage"]
        tin, tout = usage["prompt_tokens"], usage["completion_tokens"]
        rin, rout = PRICING[model]
        return (
            data["choices"][0]["message"]["content"] or "",
            cost_cents(tin, tout, rin, rout),
            tin + tout,
        )

    async def complete(self, prompt: str, max_tokens: int, temperature: float) -> TextResult:
        return await self._chat(TEXT_MODEL, prompt, max_tokens, temperature)

    async def vision(self, image_bytes: bytes, prompt: str, max_tokens: int) -> TextResult:
        url = f"data:{_sniff(image_bytes)};base64,{base64.b64encode(image_bytes).decode()}"
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": url}},
        ]
        return await self._chat(VISION_MODEL, content, max_tokens, None)

    async def embed(self, text: str) -> EmbedResult:
        data = await self._post("embeddings", {"model": EMBED_MODEL, "input": text})
        tokens = data["usage"]["prompt_tokens"]
        rin, _ = PRICING[EMBED_MODEL]
        return data["data"][0]["embedding"], cost_cents(tokens, 0, rin, 0.0), tokens

    async def count_tokens(self, text: str) -> CountResult:
        n = estimate_tokens(text)
        return n, 0.0, n
