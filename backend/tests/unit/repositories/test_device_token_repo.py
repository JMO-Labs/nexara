"""
@file test_device_token_repo.py
@brief Unit tests for DeviceTokenRepo query scoping.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

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
