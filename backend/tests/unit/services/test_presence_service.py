"""
@file test_presence_service.py
@brief PresenceService privacy mapping (repo and valkey mocked).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from app.repositories.presence_repo import PresenceRepository, PresenceRow
from app.services.presence_service import PresenceService

CID = uuid.uuid4()
NOW = datetime(2026, 11, 22, tzinfo=UTC)


async def test_flags_applied_and_self_always_visible() -> None:
    me, hidden, shown = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    repo = AsyncMock(spec=PresenceRepository)
    repo.visible.return_value = [
        PresenceRow(me, False, False, NOW),
        PresenceRow(hidden, False, False, NOW),
        PresenceRow(shown, True, True, NOW),
    ]
    with patch(
        "app.services.presence_service.online_among",
        new=AsyncMock(return_value={me, hidden, shown}),
    ):
        res = await PresenceService(repo, CID).lookup(me, [me, hidden, shown])
    assert set(res.online) == {me, shown}
    assert set(res.last_seen) == {me, shown}


async def test_offline_user_not_online() -> None:
    me, other = uuid.uuid4(), uuid.uuid4()
    repo = AsyncMock(spec=PresenceRepository)
    repo.visible.return_value = [PresenceRow(other, True, True, None)]
    with patch("app.services.presence_service.online_among", new=AsyncMock(return_value=set())):
        res = await PresenceService(repo, CID).lookup(me, [other])
    assert res.online == [] and res.last_seen == {other: None}
