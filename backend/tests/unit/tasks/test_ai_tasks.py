"""
@file test_ai_tasks.py
@brief Unit tests for the OCR Celery task.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks import ai_tasks

MID = uuid.uuid4()
CID = uuid.uuid4()


@pytest.mark.asyncio
async def test_ocr_async_runs_and_commits() -> None:
    session = AsyncMock()
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    with (
        patch.object(ai_tasks, "async_session_factory", factory),
        patch.object(ai_tasks, "get_settings"),
        patch.object(ai_tasks, "get_storage_backend"),
        patch.object(ai_tasks, "get_ai_provider", return_value=None),
        patch.object(ai_tasks, "run_ocr", new=AsyncMock(return_value="done")) as run,
    ):
        status = await ai_tasks._ocr_async(MID, CID)
    assert status == "done"
    assert run.await_args.args == (MID, CID)
    session.commit.assert_awaited_once()


def test_task_returns_status_dict() -> None:
    with patch.object(ai_tasks, "_ocr_async", new=AsyncMock(return_value="skipped")):
        out = ai_tasks.ocr_process_image(str(MID), str(CID))
    assert out == {"status": "skipped"}


def test_task_config() -> None:
    assert ai_tasks.ocr_process_image.name == "app.tasks.ai_tasks.ocr_process_image"
