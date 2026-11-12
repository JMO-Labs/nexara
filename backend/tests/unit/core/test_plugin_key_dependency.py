"""
@file test_plugin_key_dependency.py
@brief Unit tests for the get_plugin_from_api_key dependency.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.dependencies import get_plugin_from_api_key
from app.core.exceptions import AuthenticationError

KEY = "nxr_plugin_hello_" + "a" * 32


def _request(headers: dict[str, str]) -> MagicMock:
    req = MagicMock()
    req.headers = headers
    return req


async def _call(headers: dict[str, str]) -> tuple[str, AsyncMock]:
    db = AsyncMock()
    settings = Settings(SECRET_KEY="x")
    with patch(
        "app.plugins.api_keys.resolve_plugin_from_key", new=AsyncMock(return_value="hello")
    ) as resolve:
        result = await get_plugin_from_api_key(_request(headers), db, settings)
    return result, resolve


async def test_plugin_header_key() -> None:
    result, resolve = await _call({"x-plugin-api-key": KEY})
    assert result == "hello"
    assert resolve.await_args.args[1] == KEY
    assert resolve.await_args.args[2] == uuid.UUID(Settings(SECRET_KEY="x").COMMUNITY_ID)


async def test_bearer_key() -> None:
    _result, resolve = await _call({"authorization": f"Bearer {KEY}"})
    assert resolve.await_args.args[1] == KEY


async def test_missing_key_rejected() -> None:
    with pytest.raises(AuthenticationError):
        await _call({})


async def test_non_bearer_authorization_rejected() -> None:
    with pytest.raises(AuthenticationError):
        await _call({"authorization": f"Basic {KEY}"})
