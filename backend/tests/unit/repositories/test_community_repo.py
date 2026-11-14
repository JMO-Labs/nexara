"""
@file test_community_repo.py
@brief Unit tests for CommunityRepository.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.community import Community
from app.repositories.community_repo import CommunityRepository

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _session(community: Community | None) -> AsyncMock:
    session = AsyncMock()
    session.get = AsyncMock(return_value=community)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_get_returns_row():
    community = MagicMock(spec=Community)
    session = _session(community)
    assert await CommunityRepository(session).get(CID) is community
    session.get.assert_awaited_once_with(Community, CID)


@pytest.mark.asyncio
async def test_update_sets_columns_and_refreshes():
    community = MagicMock(spec=Community)
    session = _session(community)
    result = await CommunityRepository(session).update_sassybot(
        CID, {"sassybot_enabled": True, "sassybot_sass_level": 3}
    )
    assert result is community
    assert community.sassybot_enabled is True
    assert community.sassybot_sass_level == 3
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(community)


@pytest.mark.asyncio
async def test_update_missing_community_returns_none():
    session = _session(None)
    assert (
        await CommunityRepository(session).update_sassybot(CID, {"sassybot_enabled": True}) is None
    )
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_unknown_column_raises():
    session = _session(MagicMock(spec=Community))
    with pytest.raises(ValueError, match="Unknown Sassybot"):
        await CommunityRepository(session).update_sassybot(CID, {"name": "x"})
    session.get.assert_not_awaited()
