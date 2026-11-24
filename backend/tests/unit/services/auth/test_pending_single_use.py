"""
@file test_pending_single_use.py
@brief 2FA pending tokens are spent on first successful use (Valkey denylist).
"""

from __future__ import annotations

import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthenticationError
from app.services.auth import totp_replay as tr


async def test_first_use_sets_ttl_and_clears_attempts() -> None:
    redis = MagicMock()
    redis.set = AsyncMock(return_value=True)
    uid = uuid.uuid4()
    with (
        patch.object(tr, "get_pool", return_value=redis),
        patch.object(tr, "clear_user_attempts", AsyncMock()) as clear,
    ):
        await tr.finish_pending("tok", {"exp": time.time() + 120}, uid, MagicMock())
    kw = redis.set.call_args.kwargs
    assert kw["nx"] is True and 100 <= kw["ex"] <= 122
    clear.assert_awaited_once()


async def test_second_use_rejected() -> None:
    redis = MagicMock()
    redis.set = AsyncMock(return_value=None)
    with (
        patch.object(tr, "get_pool", return_value=redis),
        patch.object(tr, "clear_user_attempts", AsyncMock()) as clear,
        pytest.raises(AuthenticationError),
    ):
        await tr.finish_pending("tok", {"exp": time.time() + 120}, uuid.uuid4(), MagicMock())
    clear.assert_not_awaited()
