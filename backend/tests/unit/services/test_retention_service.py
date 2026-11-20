"""
@file test_retention_service.py
@brief Unit tests for RetentionService.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import NotFoundError
from app.models.retention import RetentionPolicy
from app.repositories.retention_repo import RetentionRepository
from app.schemas.admin_retention import RetentionUpdate
from app.services.retention_service import DEFAULT_POLICIES, RetentionService


def _row(key: str, days: int | None = 30) -> MagicMock:
    row = MagicMock(spec=RetentionPolicy)
    row.policy_key = key
    row.enabled = True
    row.retention_days = days
    row.delete_media_files = False
    row.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    row.updated_by = None
    return row


@pytest.fixture
def repo():
    return AsyncMock(spec=RetentionRepository)


async def test_list_returns_all_known_keys_with_defaults(repo):
    repo.list_all.return_value = []
    out = await RetentionService(repo).list_policies()
    assert {p.policy_key for p in out} == set(DEFAULT_POLICIES)
    assert len(out) == 12


async def test_list_prefers_stored_row_over_default(repo):
    repo.list_all.return_value = [_row("chat_messages", 99)]
    out = await RetentionService(repo).list_policies()
    chat = next(p for p in out if p.policy_key == "chat_messages")
    assert chat.retention_days == 99


async def test_update_unknown_key_raises_not_found(repo):
    with pytest.raises(NotFoundError):
        await RetentionService(repo).update(
            "bogus",
            RetentionUpdate(enabled=True, retention_days=5, delete_media_files=False),
            uuid.uuid4(),
        )
    repo.upsert.assert_not_called()


async def test_update_upserts_and_returns(repo):
    uid = uuid.uuid4()
    repo.upsert.return_value = _row("notifications", 14)
    body = RetentionUpdate(enabled=True, retention_days=14, delete_media_files=False)
    out = await RetentionService(repo).update("notifications", body, uid)
    repo.upsert.assert_awaited_once_with("notifications", True, 14, False, uid)
    assert out.retention_days == 14
