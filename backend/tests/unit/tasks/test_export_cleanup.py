"""
@file test_export_cleanup.py
@brief Tests for the expired-export cleanup task and its beat entry.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.tasks import maintenance_tasks as mt
from app.tasks.celery_app import celery_app


def _row(key="exports/a.zip"):
    r = MagicMock()
    r.file_key = key
    return r


async def test_cleanup_deletes_files_and_rows():
    rows = [_row("a"), _row("b")]
    repo = MagicMock()
    repo.list_expired = AsyncMock(return_value=rows)
    repo.delete_row = AsyncMock()
    repo.commit = AsyncMock()
    storage = AsyncMock()
    count = await mt._cleanup_expired_exports_async(repo, storage)
    assert count == 2
    assert [c.args[0] for c in storage.delete.await_args_list] == ["a", "b"]
    assert repo.delete_row.await_count == 2
    repo.commit.assert_awaited_once()


async def test_cleanup_keeps_row_when_storage_fails():
    rows = [_row("a"), _row("b")]
    repo = MagicMock()
    repo.list_expired = AsyncMock(return_value=rows)
    repo.delete_row = AsyncMock()
    repo.commit = AsyncMock()
    storage = AsyncMock()
    storage.delete.side_effect = [RuntimeError("x"), None]
    assert await mt._cleanup_expired_exports_async(repo, storage) == 1
    repo.delete_row.assert_awaited_once_with(rows[1])


def test_task_registered_and_scheduled():
    entry = celery_app.conf.beat_schedule["cleanup-expired-exports"]
    assert entry["task"] == "app.tasks.maintenance_tasks.cleanup_expired_exports"
    assert entry["schedule"].hour == {0} and entry["schedule"].minute == {30}
    assert mt.cleanup_expired_exports.queue == "maintenance"


def test_cleanup_task_runs_and_reports_count(monkeypatch):
    from unittest.mock import patch

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=MagicMock())
    session_cm.__aexit__ = AsyncMock(return_value=False)
    with (
        patch("app.db.session.async_session_factory", return_value=session_cm),
        patch("app.services.storage.factory.get_storage_backend"),
        patch.object(mt, "_cleanup_expired_exports_async", AsyncMock(return_value=3)),
        patch("app.core.metrics.export_cleanup_total") as metric,
    ):
        assert mt.cleanup_expired_exports() == {"deleted_count": 3}
    metric.inc.assert_called_once_with(3)
