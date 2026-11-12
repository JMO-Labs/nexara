"""
@file test_device_token_repo.py
@brief Unit tests for DeviceTokenRepo query scoping.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.device_token import DeviceToken
from app.repositories.device_token_repo import DeviceTokenRepo


async def test_find_active_filters_community_user_and_deleted():
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)
    repo = DeviceTokenRepo(session)

    await repo.find_active(uuid.uuid4(), uuid.uuid4(), "tok")

    sql = str(session.execute.await_args.args[0])
    assert "device_tokens.community_id" in sql
    assert "device_tokens.user_id" in sql
    assert "device_tokens.deleted_at IS NULL" in sql


async def test_find_by_token_returns_row_ignoring_state():
    row = MagicMock(spec=DeviceToken)
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalar_one_or_none=lambda: row)
    repo = DeviceTokenRepo(session)

    assert await repo.find_by_token("tok") is row

    sql = str(session.execute.await_args.args[0])
    assert "device_tokens.token" in sql
    where = sql.split("WHERE", 1)[1]
    assert "device_tokens.token" in where
    assert "deleted_at" not in where
    assert "community_id" not in where


async def test_reassign_updates_owner_and_revives():
    session = AsyncMock()
    repo = DeviceTokenRepo(session)
    device = MagicMock(spec=DeviceToken)
    device.deleted_at = "gone"
    user_id, community_id = uuid.uuid4(), uuid.uuid4()

    out = await repo.reassign(device, user_id=user_id, community_id=community_id, platform="ios")

    assert out is device
    assert device.user_id == user_id
    assert device.community_id == community_id
    assert device.platform == "ios"
    assert device.deleted_at is None
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(device)


async def test_list_active_for_user_scopes_and_returns_list():
    rows = [MagicMock(spec=DeviceToken), MagicMock(spec=DeviceToken)]
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: rows))
    repo = DeviceTokenRepo(session)

    out = await repo.list_active_for_user(uuid.uuid4(), uuid.uuid4())

    assert out == rows
    sql = str(session.execute.await_args.args[0])
    assert "device_tokens.community_id" in sql
    assert "device_tokens.user_id" in sql
    assert "device_tokens.deleted_at IS NULL" in sql
