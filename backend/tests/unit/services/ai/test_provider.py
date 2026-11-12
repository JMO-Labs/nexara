"""
@file test_provider.py
@brief Unit tests for get_ai_provider registry lookup.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.ai import provider as prov


class _Fake:
    async def vision(self, image: bytes, prompt: str, *, max_tokens: int = 1000) -> str:
        return "x"


def test_disabled_returns_none() -> None:
    assert prov.get_ai_provider(MagicMock(AI_PROVIDER="")) is None


def test_unknown_provider_returns_none() -> None:
    assert prov.get_ai_provider(MagicMock(AI_PROVIDER="nope")) is None


def test_registered_provider_instantiated() -> None:
    with patch.dict(prov._PROVIDERS, {"fake": _Fake}):
        out = prov.get_ai_provider(MagicMock(AI_PROVIDER="fake"))
    assert isinstance(out, _Fake)
    assert isinstance(out, prov.AIProvider)
