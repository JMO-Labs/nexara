"""
@file test_ocr.py
@brief Unit tests for the OCR pipeline (task logic, enqueue, repository FTS).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.dialects import postgresql

from app.models.media import Media
from app.models.media_ai import MediaAIMetadata
from app.repositories.media_ai_repo import MediaAIRepository
from app.repositories.media_repo import MediaRepository
from app.services.ai.ocr import OCR_PROMPT, run_ocr
from app.services.ai.provider import AIBudgetExhaustedError, AIError, AIProvider
from app.services.storage.base import StorageBackend

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _deps(content_type: str = "image/png"):
    media = MagicMock(spec=Media)
    media.id = uuid.uuid4()
    media.content_type = content_type
    media.storage_key = "k/a.png"
    media_repo = AsyncMock(spec=MediaRepository)
    media_repo.get_by_id.return_value = media
    ai_repo = AsyncMock(spec=MediaAIRepository)
    ai_repo.get_by_media_id.return_value = None
    storage = AsyncMock(spec=StorageBackend)
    storage.get.return_value = b"img"
    provider = AsyncMock(spec=AIProvider)
    provider.vision.return_value = ("hello\nworld", 0.1, 10)
    return media, media_repo, ai_repo, storage, provider


async def test_ocr_extracts_and_stores() -> None:
    media, mr, ar, st, pr = _deps()
    res = await run_ocr(media.id, CID, media_repo=mr, ai_repo=ar, storage=st, provider=pr)
    assert res == "processed"
    pr.vision.assert_awaited_once_with(b"img", OCR_PROMPT, max_tokens=2000)
    kw = ar.create.await_args.kwargs
    assert kw["ocr_text"] == "hello\nworld"
    assert kw["community_id"] == CID
    assert kw["processed_at"] is not None


async def test_ocr_skipped_when_ai_not_configured() -> None:
    media, mr, ar, st, _ = _deps()
    res = await run_ocr(media.id, CID, media_repo=mr, ai_repo=ar, storage=st, provider=None)
    assert res == "skipped"
    ar.create.assert_not_awaited()


async def test_ocr_skips_non_image() -> None:
    media, mr, ar, st, pr = _deps("video/mp4")
    assert (
        await run_ocr(media.id, CID, media_repo=mr, ai_repo=ar, storage=st, provider=pr)
        == "skipped"
    )
    pr.vision.assert_not_awaited()


async def test_ocr_ai_error_does_not_raise() -> None:
    media, mr, ar, st, pr = _deps()
    pr.vision.side_effect = AIError("boom")
    res = await run_ocr(media.id, CID, media_repo=mr, ai_repo=ar, storage=st, provider=pr)
    assert res == "error"
    ar.create.assert_not_awaited()


async def test_ocr_budget_exhausted_skips() -> None:
    media, mr, ar, st, pr = _deps()
    pr.vision.side_effect = AIBudgetExhaustedError("budget")
    res = await run_ocr(media.id, CID, media_repo=mr, ai_repo=ar, storage=st, provider=pr)
    assert res == "budget_exhausted"
    ar.create.assert_not_awaited()


async def test_ocr_uses_community_scoped_lookup_and_skips_mismatch() -> None:
    media, mr, ar, st, pr = _deps()
    mr.get_by_id.return_value = None  # other tenant: scoped lookup finds nothing
    res = await run_ocr(media.id, CID, media_repo=mr, ai_repo=ar, storage=st, provider=pr)
    mr.get_by_id.assert_awaited_once_with(media.id, CID)
    assert res == "skipped"
    ar.create.assert_not_awaited()


async def test_ocr_skips_when_already_processed() -> None:
    media, mr, ar, st, pr = _deps()
    ar.get_by_media_id.return_value = MagicMock(spec=MediaAIMetadata)
    res = await run_ocr(media.id, CID, media_repo=mr, ai_repo=ar, storage=st, provider=pr)
    assert res == "skipped"
    pr.vision.assert_not_awaited()
    ar.create.assert_not_awaited()


async def test_fts_query_targets_ocr_fts() -> None:
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [MagicMock(spec=MediaAIMetadata)]
    session.execute.return_value = result
    out = await MediaAIRepository(session).search_by_fts("invoice", CID, limit=5, offset=0)
    assert len(out) == 1
    sql = str(session.execute.await_args.args[0].compile(dialect=postgresql.dialect()))
    assert "ocr_fts @@" in sql and "community_id" in sql


def test_enqueue_helper_routes_to_media_queue_when_configured() -> None:
    from app.services.media_service import enqueue_ocr

    cid = uuid.uuid4()
    with (
        patch("app.services.media_service.ocr_process_image") as task,
        patch("app.services.media_service.get_settings") as gs,
    ):
        gs.return_value.AI_PROVIDER = "x"
        enqueue_ocr(uuid.uuid4(), cid, "image/png")
        task.apply_async.assert_called_once()
        assert task.apply_async.call_args.kwargs["queue"] == "media"
        assert task.apply_async.call_args.kwargs["time_limit"] == 3600
        task.reset_mock()
        enqueue_ocr(uuid.uuid4(), cid, "video/mp4")
        gs.return_value.AI_PROVIDER = ""
        enqueue_ocr(uuid.uuid4(), cid, "image/png")
        task.apply_async.assert_not_called()
