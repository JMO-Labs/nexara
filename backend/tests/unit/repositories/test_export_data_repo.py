"""
@file test_export_data_repo.py
@brief Unit tests for ExportDataRepository (session mocked).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.repositories.export_data_repo import ExportDataRepository

UID, CID = uuid.uuid4(), uuid.uuid4()
MOD = "app.repositories.export_data_repo"


async def _agen(items):
    for i in items:
        yield i


def _repo(rows=()):
    session = AsyncMock()
    session.stream_scalars.return_value = _agen(rows)
    return ExportDataRepository(session), session


@pytest.mark.parametrize(
    "method",
    ["list_posts", "list_comments", "list_reactions", "list_events", "list_rsvps", "list_media"],
)
async def test_list_methods_serialize_rows(method) -> None:
    repo, session = _repo([object(), object()])
    with patch(f"{MOD}.serialize", side_effect=[{"a": 1}, {"a": 2}]):
        out = await getattr(repo, method)(UID, CID)
    assert out == [{"a": 1}, {"a": 2}]
    session.stream_scalars.assert_awaited_once()


async def test_get_profile_returns_serialized_user() -> None:
    repo, session = _repo()
    session.get.return_value = MagicMock(community_id=CID)
    with patch(f"{MOD}.serialize", return_value={"id": "x"}):
        assert await repo.get_profile(UID, CID) == {"id": "x"}


async def test_get_profile_missing_user_raises() -> None:
    repo, session = _repo()
    session.get.return_value = None
    with pytest.raises(LookupError):
        await repo.get_profile(UID, CID)


async def test_get_profile_other_community_raises() -> None:
    repo, session = _repo()
    session.get.return_value = MagicMock(community_id=uuid.uuid4())
    with pytest.raises(LookupError):
        await repo.get_profile(UID, CID)
