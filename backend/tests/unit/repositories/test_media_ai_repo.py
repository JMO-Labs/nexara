"""
@file test_media_ai_repo.py
@brief Unit tests for MediaAIRepository.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.media_ai_repo import MediaAIRepository

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_get_by_media_id_returns_scalar() -> None:
    session = _session()
    result = MagicMock()
    result.scalar_one_or_none.return_value = "row"
    session.execute = AsyncMock(return_value=result)
    out = await MediaAIRepository(session).get_by_media_id(uuid.uuid4())
    assert out == "row"
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_adds_flushes_and_refreshes() -> None:
    session = _session()
    mid = uuid.uuid4()
    row = await MediaAIRepository(session).create(
        mid, community_id=CID, ocr_text="hi", description="d", tags=["a"]
    )
    session.add.assert_called_once_with(row)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(row)
    assert (row.media_id, row.community_id, row.ocr_text) == (mid, CID, "hi")
