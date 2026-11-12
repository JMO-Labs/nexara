"""
@file test_ai_coverage.py
@brief Cover remaining OCR/AI lines: repo, provider factory, enqueue, task.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.repositories.media_ai_repo import MediaAIRepository
from app.services.ai import provider as prov

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
    s.execute.assert_awaited_once()


async def test_create_adds_flushes_refreshes() -> None:
    s = _session()
    mid = uuid.uuid4()
    row = await MediaAIRepository(s).create(
        mid, community_id=CID, ocr_text="hi", description="d", tags=["a"]
    )
    assert row.media_id == mid and row.ocr_text == "hi" and row.community_id == CID
    s.add.assert_called_once_with(row)
    s.flush.assert_awaited_once()
    s.refresh.assert_awaited_once_with(row)


def test_get_ai_provider_disabled_returns_none() -> None:
    assert prov.get_ai_provider(MagicMock(AI_PROVIDER="")) is None


def test_get_ai_provider_unknown_returns_none() -> None:
    assert prov.get_ai_provider(MagicMock(AI_PROVIDER="nope")) is None


def test_get_ai_provider_misconfigured_returns_none() -> None:
    settings = MagicMock(AI_PROVIDER="anthropic", ANTHROPIC_API_KEY="")
    assert prov.get_ai_provider(settings) is None


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


async def test_ocr_async_wires_dependencies_and_commits() -> None:
    from app.tasks import ai_tasks

    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    mid = uuid.uuid4()
    redis = MagicMock(aclose=AsyncMock())
    with (
        patch.object(ai_tasks, "get_settings"),
        patch.object(ai_tasks, "create_pool", return_value=redis),
        patch.object(ai_tasks, "BudgetService"),
        patch.object(ai_tasks, "async_session_factory", return_value=cm),
        patch.object(ai_tasks, "get_storage_backend"),
        patch.object(ai_tasks, "get_ai_provider"),
        patch.object(ai_tasks, "run_ocr", AsyncMock(return_value="processed")) as run,
    ):
        assert await ai_tasks._ocr_async(mid, CID) == "processed"
    assert run.await_args.args == (mid, CID)
    session.commit.assert_awaited_once()
    redis.aclose.assert_awaited_once()


def test_ocr_task_returns_status_dict() -> None:
    from app.tasks import ai_tasks

    mid = uuid.uuid4()
    with (
        patch.object(ai_tasks, "_ocr_async", new=MagicMock(return_value=object())),
        patch.object(ai_tasks.asyncio, "run", return_value="skipped") as run,
    ):
        out = ai_tasks.ocr_process_image(str(mid), str(CID))
    assert out == {"status": "skipped"}
    run.assert_called_once()
    assert ai_tasks.ocr_process_image.name == "app.tasks.ai_tasks.ocr_process_image"


@pytest.mark.parametrize("exc", [prov.AIBudgetExhaustedError, prov.AIError])
def test_error_hierarchy(exc: type[Exception]) -> None:
    assert issubclass(exc, prov.AIError)
