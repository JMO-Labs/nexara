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
    assert "deleted_at" not in sql
    assert "community_id" not in sql


async def test_reassign_updates_fields_revives_and_refreshes():
    device = MagicMock(spec=DeviceToken)
    device.deleted_at = object()
    session = AsyncMock()
    repo = DeviceTokenRepo(session)
    user_id, community_id = uuid.uuid4(), uuid.uuid4()

    result = await repo.reassign(device, user_id=user_id, community_id=community_id, platform="ios")

    assert result is device
    assert device.user_id == user_id
    assert device.community_id == community_id
    assert device.platform == "ios"
    assert device.deleted_at is None
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(device)
