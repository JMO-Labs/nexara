"""
@file test_ocr_coverage.py
@brief Covers repo, provider registry, enqueue failure and OCR task glue.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.repositories.media_ai_repo import MediaAIRepository
from app.services.ai import provider as provider_mod
from app.tasks import ai_tasks

CID = uuid.uuid4()


def _session() -> AsyncMock:
    s = AsyncMock()
    s.add = MagicMock()
    return s


async def test_get_by_media_id_returns_scalar() -> None:
    s = _session()
    res = MagicMock()
    res.scalar_one_or_none.return_value = "row"
    s.execute.return_value = res
    assert await MediaAIRepository(s).get_by_media_id(uuid.uuid4()) == "row"


async def test_create_adds_flushes_refreshes() -> None:
    s = _session()
    mid = uuid.uuid4()
    row = await MediaAIRepository(s).create(mid, community_id=CID, ocr_text="hi")
    assert row.media_id == mid and row.ocr_text == "hi"
    s.add.assert_called_once_with(row)
    s.flush.assert_awaited_once()
    s.refresh.assert_awaited_once_with(row)


def test_get_ai_provider_none_when_unset() -> None:
    assert provider_mod.get_ai_provider(MagicMock(AI_PROVIDER="")) is None


def test_get_ai_provider_unknown_returns_none() -> None:
    assert provider_mod.get_ai_provider(MagicMock(AI_PROVIDER="nope")) is None


def test_get_ai_provider_registered_instantiates() -> None:
    class Fake:
        pass

    with patch.dict(provider_mod._PROVIDERS, {"fake": Fake}):
        assert isinstance(provider_mod.get_ai_provider(MagicMock(AI_PROVIDER="fake")), Fake)


def test_enqueue_ocr_swallows_broker_errors() -> None:
    from app.services.media_service import enqueue_ocr

    with (
        patch("app.services.media_service.ocr_process_image") as task,
        patch("app.services.media_service.get_settings") as gs,
    ):
        gs.return_value.AI_PROVIDER = "x"
        task.apply_async.side_effect = RuntimeError("broker down")
        enqueue_ocr(uuid.uuid4(), CID, "image/png")  # must not raise
        task.apply_async.assert_called_once()


async def test_ocr_async_runs_and_commits() -> None:
    session = AsyncMock()
    factory = MagicMock()
    factory.return_value.__aenter__.return_value = session
    with (
        patch.object(ai_tasks, "async_session_factory", factory),
        patch.object(ai_tasks, "get_settings"),
        patch.object(ai_tasks, "get_storage_backend"),
        patch.object(ai_tasks, "get_ai_provider"),
        patch.object(ai_tasks, "run_ocr", AsyncMock(return_value="done")) as run,
    ):
        assert await ai_tasks._ocr_async(uuid.uuid4(), CID) == "done"
    run.assert_awaited_once()
    session.commit.assert_awaited_once()


def test_ocr_process_image_returns_status() -> None:
    mid = uuid.uuid4()
    with patch.object(ai_tasks, "_ocr_async", new=MagicMock(return_value=None)) as m, patch.object(
        ai_tasks.asyncio, "run", return_value="skipped"
    ) as run:
        assert ai_tasks.ocr_process_image(str(mid), str(CID)) == {"status": "skipped"}
    m.assert_called_once_with(mid, CID)
    run.assert_called_once()
