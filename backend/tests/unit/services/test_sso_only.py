"""
@file test_sso_only.py
@brief Unit tests for SSO-only helpers (provider count, flag write, toggle).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError
from app.services.auth import sso_only

CID = uuid.uuid4()


def _session(scalar=None, rowcount=1):
    res = MagicMock()
    res.scalar_one.return_value = scalar
    res.rowcount = rowcount
    s = AsyncMock()
    s.execute.return_value = res
    s.add = MagicMock()
    return s


async def test_count_enabled_providers_returns_int():
    s = _session(scalar=3)
    assert await sso_only.count_enabled_providers(s, CID) == 3
    s.execute.assert_awaited_once()


async def test_write_flag_updates_existing_row():
    s = _session(rowcount=1)
    await sso_only.write_flag(s, CID, True, uuid.uuid4())
    s.add.assert_not_called()
    s.flush.assert_awaited_once()


async def test_write_flag_creates_row_when_missing():
    s = _session(rowcount=0)
    await sso_only.write_flag(s, CID, True, None)
    added = s.add.call_args.args[0]
    assert added.community_id == CID
    assert added.sso_only is True
    s.flush.assert_awaited_once()


async def test_set_sso_only_rejects_without_provider():
    s = _session(scalar=0)
    with pytest.raises(AppError) as exc:
        await sso_only.set_sso_only(s, CID, True, None)
    assert exc.value.status_code == 422
    s.flush.assert_not_awaited()


async def test_set_sso_only_enables_with_provider():
    s = _session(scalar=1)
    await sso_only.set_sso_only(s, CID, True, None)
    s.flush.assert_awaited_once()


async def test_set_sso_only_disable_skips_provider_check():
    s = _session(rowcount=1)
    await sso_only.set_sso_only(s, CID, False, None)
    assert s.execute.await_count == 1
