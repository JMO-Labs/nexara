"""
@file test_backup_code_atomic.py
@brief Backup-code consumption is a single atomic UPDATE ... RETURNING.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.dml import Update

from app.services.auth.totp_replay import consume_backup_code


def _session(returned: object | None) -> AsyncMock:
    s = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = returned
    res.first.return_value = (returned,) if returned else None
    s.execute.return_value = res
    return s


@pytest.mark.asyncio
async def test_consume_is_one_conditional_update():
    s = _session(uuid.uuid4())
    assert await consume_backup_code(s, uuid.uuid4(), "ABCD1234") is True
    s.execute.assert_awaited_once()
    stmt = s.execute.await_args.args[0]
    assert isinstance(stmt, Update)
    assert "used_at IS NULL" in str(stmt)
    assert "RETURNING" in str(stmt.compile())


@pytest.mark.asyncio
async def test_lost_race_returns_false():
    s = _session(None)  # row already spent by a concurrent request
    assert await consume_backup_code(s, uuid.uuid4(), "ABCD1234") is False
