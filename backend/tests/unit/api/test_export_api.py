"""
@file test_export_api.py
@brief Unit tests for the export API handlers and the export Celery task.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1 import export as api
from app.core.exceptions import AuthorizationError, NotFoundError, RateLimitError

NOW = datetime.now(UTC)


def _user() -> MagicMock:
    user = MagicMock()
    user.id, user.community_id = uuid.uuid4(), uuid.uuid4()
    return user


def _row(user_id: uuid.UUID, status: str = "ready", expires: datetime | None = None) -> MagicMock:
    row = MagicMock()
    row.id, row.user_id, row.status = uuid.uuid4(), user_id, status
    row.created_at, row.ready_at, row.expires_at = NOW, NOW, expires
    row.file_size_bytes = 5
    return row


def test_get_repo_and_redis_and_enqueue_factories() -> None:
    db = MagicMock()
    assert api._get_repo(db)._session is db
    with patch.object(api, "get_pool", return_value="pool") as pool:
        assert api._get_redis() == "pool"
        pool.assert_called_once()
    with patch("app.tasks.export_tasks.generate_user_export") as task:
        api._get_enqueue()("u1", "e1")
        task.apply_async.assert_called_once_with(("u1", "e1"), queue="default")


async def test_request_export_creates_and_enqueues() -> None:
    user = _user()
    row = _row(user.id, "pending")
    repo, redis, enqueue = AsyncMock(), AsyncMock(), MagicMock()
    repo.create.return_value = row
    redis.set.return_value = True
    out = await api.request_export(user, repo, redis, enqueue)
    assert out.export_id == row.id
    repo.commit.assert_awaited_once()
    enqueue.assert_called_once_with(str(user.id), str(row.id))


async def test_request_export_rate_limited() -> None:
    redis, repo = AsyncMock(), AsyncMock()
    redis.set.return_value = None
    with pytest.raises(RateLimitError):
        await api.request_export(_user(), repo, redis, MagicMock())
    repo.create.assert_not_awaited()


async def test_request_export_failure_releases_key() -> None:
    redis, repo = AsyncMock(), AsyncMock()
    redis.set.return_value = True
    repo.create.side_effect = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        await api.request_export(_user(), repo, redis, MagicMock())
    redis.delete.assert_awaited_once()


async def test_status_not_found() -> None:
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        await api.export_status(uuid.uuid4(), _user(), repo)


async def test_status_other_user_forbidden() -> None:
    repo = AsyncMock()
    repo.get_by_id.return_value = _row(uuid.uuid4())
    with pytest.raises(AuthorizationError):
        await api.export_status(uuid.uuid4(), _user(), repo)


async def test_status_ready_has_download_url() -> None:
    user = _user()
    row = _row(user.id, expires=NOW + timedelta(days=1))
    repo = AsyncMock()
    repo.get_by_id.return_value = row
    out = await api.export_status(row.id, user, repo)
    assert out.status == "ready"
    assert out.download_url == f"/api/v1/export/{row.id}/download"


async def test_status_ready_but_expired() -> None:
    user = _user()
    row = _row(user.id, expires=NOW - timedelta(seconds=1))
    repo = AsyncMock()
    repo.get_by_id.return_value = row
    out = await api.export_status(row.id, user, repo)
    assert (out.status, out.download_url) == ("expired", None)


async def test_status_pending_no_url() -> None:
    user = _user()
    row = _row(user.id, "pending")
    repo = AsyncMock()
    repo.get_by_id.return_value = row
    assert (await api.export_status(row.id, user, repo)).download_url is None
