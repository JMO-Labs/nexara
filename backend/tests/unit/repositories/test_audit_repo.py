"""
@file test_audit_repo.py
@brief Unit tests for AuditRepository.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.audit import AuditLog
from app.repositories.audit_repo import AuditRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ACTOR_ID = uuid.uuid4()
TARGET_ID = uuid.uuid4()


def _make_session() -> AsyncMock:
    """@brief Create a mock AsyncSession with flush/refresh/execute stubs."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


class TestAppend:
    """@brief Tests for AuditRepository.append()."""

    @pytest.mark.asyncio
    async def test_creates_audit_entry_with_all_fields(self):
        """append should create an audit entry with all provided fields."""
        session = _make_session()
        repo = AuditRepository(session)

        result = await repo.append(
            actor_id=ACTOR_ID,
            action="admin.user.role_changed",
            target_type="user",
            target_id=TARGET_ID,
            extra_data={"old_role": "member", "new_role": "admin"},
            ip_address="192.168.1.1",
        )

        assert isinstance(result, AuditLog)
        assert result.actor_id == ACTOR_ID
        assert result.action == "admin.user.role_changed"
        assert result.target_type == "user"
        assert result.target_id == TARGET_ID
        assert result.extra_data == {"old_role": "member", "new_role": "admin"}
        assert result.ip_address == "192.168.1.1"
        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once()


class TestListEntries:
    """@brief Tests for AuditRepository.list_entries()."""

    @pytest.mark.asyncio
    async def test_returns_paginated_entries(self):
        """list_entries should return paginated audit entries."""
        session = _make_session()
        entry1 = MagicMock(spec=AuditLog)
        entry1.id = uuid.uuid4()
        entry2 = MagicMock(spec=AuditLog)
        entry2.id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [entry1, entry2]
        session.execute.return_value = mock_result

        repo = AuditRepository(session)
        entries, next_cursor = await repo.list_entries(limit=2)

        assert len(entries) == 2
        assert entries[0] is entry1
        assert entries[1] is entry2
        assert next_cursor is None
        session.execute.assert_awaited_once()
