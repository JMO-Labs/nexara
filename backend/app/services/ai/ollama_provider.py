"""
@file ollama_provider.py
@brief Self-hosted Ollama provider (no cost tracking).
"""

from __future__ import annotations

import base64
from typing import Any, cast

import httpx

from app.services.ai.provider import (
    AIProvider,
    CountResult,
    EmbedResult,
    TextResult,
    estimate_tokens,
)


class OllamaProvider(AIProvider):
    """@brief Ollama REST provider; cost is always 0.0."""

    def __init__(
        self,
        base_url: str,
        model: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._model = model
        self.vision_model = model
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def _post(self, path: str, body: dict[str, object]) -> dict[str, Any]:
        resp = await self._client.post(f"{self._base}/api/{path}", json=body)
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())

    async def _generate(self, body: dict[str, object]) -> TextResult:
        data = await self._post("generate", {"model": self._model, "stream": False, **body})
        tokens = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
        return data["response"], 0.0, tokens

    async def complete(self, prompt: str, max_tokens: int, temperature: float) -> TextResult:
        opts = {"num_predict": max_tokens, "temperature": temperature}
        return await self._generate({"prompt": prompt, "options": opts})

    async def vision(self, image_bytes: bytes, prompt: str, max_tokens: int) -> TextResult:
        return await self._generate(
            {
                "prompt": prompt,
                "images": [base64.b64encode(image_bytes).decode()],
                "options": {"num_predict": max_tokens},
            }
        )

    async def embed(self, text: str) -> EmbedResult:
        data = await self._post("embeddings", {"model": self._model, "prompt": text})
        return data["embedding"], 0.0, estimate_tokens(text)

    async def count_tokens(self, text: str) -> CountResult:
        n = estimate_tokens(text)
        return n, 0.0, n
