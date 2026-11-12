"""
@file test_export_tasks.py
@brief Unit tests for the generate_user_export Celery task.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks import export_tasks

UID, EID = uuid.uuid4(), uuid.uuid4()
MOD = "app.tasks.export_tasks"


@pytest.fixture
def deps():
    export_repo = AsyncMock()
    notif = AsyncMock()
    storage = AsyncMock()
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    export_repo.get_by_id.return_value = MagicMock(id=EID, user_id=UID, community_id=uuid.uuid4())
    with (
        patch(f"{MOD}.async_session_factory", return_value=session),
        patch(f"{MOD}.UserExportRepository", return_value=export_repo),
        patch(f"{MOD}.ExportDataRepository"),
        patch(f"{MOD}._notifier", return_value=notif),
        patch(f"{MOD}.get_storage_backend", return_value=storage),
        patch(f"{MOD}.build_export_archive", new=AsyncMock()) as build,
    ):
        yield export_repo, notif, storage, build


def test_registered_on_default_queue():
    task = export_tasks.generate_user_export
    assert task.queue == "default"
    assert task.time_limit == 3600


async def test_success_updates_record_and_notifies(deps):
    repo, notif, storage, _ = deps
    await export_tasks._generate(str(UID), str(EID))
    statuses = [c.args[1] for c in repo.update_status.await_args_list]
    assert statuses == ["processing", "ready"]
    ready = repo.update_status.await_args_list[-1].kwargs
    assert ready["file_key"] == f"exports/{UID}/{EID}.zip"
    assert ready["file_size_bytes"] is not None
    assert ready["expires_at"] > ready["ready_at"]
    storage.put.assert_awaited_once()
    assert notif.notify.await_args.kwargs["type"] == "data_export_ready"


async def test_failure_marks_failed_and_notifies(deps):
    repo, notif, _, build = deps
    build.side_effect = RuntimeError("boom")
    await export_tasks._generate(str(UID), str(EID))
    last = repo.update_status.await_args_list[-1]
    assert last.args[1] == "failed"
    assert last.kwargs["error_message"] == "boom"
    assert notif.notify.await_args.kwargs["type"] == "data_export_failed"
