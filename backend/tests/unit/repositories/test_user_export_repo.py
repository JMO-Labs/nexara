"""
@file test_user_export_repo.py
@brief Unit tests for UserExportRepository (session mocked). Real-DB checks live in
       tests/integration/repositories/test_user_export_repo.py.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.user_export import UserExport
from app.repositories.user_export_repo import UserExportRepository

CID = uuid.uuid4()
UID = uuid.uuid4()


def _repo(found: object = None) -> tuple[UserExportRepository, AsyncMock]:
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.return_value = MagicMock(scalar_one_or_none=lambda: found)
    return UserExportRepository(session), session


async def test_create_pending_flushes_refreshes() -> None:
    repo, session = _repo()
    row = await repo.create(UID, CID)
    assert isinstance(row, UserExport)
    assert (row.user_id, row.community_id, row.status) == (UID, CID, "pending")
    session.add.assert_called_once_with(row)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(row)


async def test_get_by_id_scoped_to_community() -> None:
    repo, session = _repo()
    await repo.get_by_id(uuid.uuid4(), CID)
    assert "user_exports.community_id" in str(session.execute.await_args.args[0])


async def test_get_latest_by_user_scoped_newest_first() -> None:
    repo, session = _repo()
    await repo.get_latest_by_user(UID, CID)
    sql = str(session.execute.await_args.args[0])
    assert "user_exports.user_id" in sql
    assert "user_exports.community_id" in sql
    assert "ORDER BY user_exports.created_at DESC" in sql


async def test_update_status_sets_given_fields_only() -> None:
    row = UserExport(user_id=UID, community_id=CID, status="pending", file_key="keep")
    repo, session = _repo(row)
    now = datetime.now(UTC)
    out = await repo.update_status(row.id, "ready", file_size_bytes=7, ready_at=now)
    assert out is row
    assert (row.status, row.file_size_bytes, row.ready_at, row.file_key) == (
        "ready",
        7,
        now,
        "keep",
    )
    session.flush.assert_awaited_once()


async def test_update_status_missing_raises() -> None:
    repo, _ = _repo(None)
    with pytest.raises(LookupError):
        await repo.update_status(uuid.uuid4(), "failed")


async def test_commit_commits_session() -> None:
    repo, session = _repo()
    await repo.commit()
    session.commit.assert_awaited_once()


async def test_mark_downloaded_stamps_and_flushes() -> None:
    row = UserExport(user_id=UID, community_id=CID, status="ready")
    repo, session = _repo()
    await repo.mark_downloaded(row)
    assert row.downloaded_at is not None
    session.flush.assert_awaited_once()


async def test_list_expired_filters_on_ready_at_and_file_key() -> None:
    rows = [UserExport(user_id=UID, community_id=CID, status="ready")]
    repo, session = _repo()
    session.execute.return_value = MagicMock(
        scalars=lambda: MagicMock(all=lambda: rows)
    )
    assert await repo.list_expired(datetime.now(UTC)) == rows
    sql = str(session.execute.await_args.args[0])
    assert "ready_at <" in sql and "file_key IS NOT NULL" in sql


async def test_delete_row_deletes_and_flushes() -> None:
    row = UserExport(user_id=UID, community_id=CID, status="ready")
    repo, session = _repo()
    await repo.delete_row(row)
    session.delete.assert_awaited_once_with(row)
    session.flush.assert_awaited_once()
