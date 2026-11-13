"""
@file test_users_blocked.py
@brief Unit test for the users.py list_blocked_users handler (nexara#384).

The moderation router registers GET /users/blocked first and shadows the
users.py route, so the handler is invoked directly.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.api.v1.users import list_blocked_users
from app.models.user import User


async def test_list_blocked_users_delegates_to_service():
    user = MagicMock(spec=User)
    blocked = [MagicMock(spec=User)]
    svc = AsyncMock()
    svc.list_blocked.return_value = blocked

    result = await list_blocked_users(user=user, svc=svc)

    assert result is blocked
    svc.list_blocked.assert_awaited_once_with(user)
