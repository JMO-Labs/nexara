"""
@file test_media_tasks_cache.py
@brief Media tasks invalidate the search cache on ready with their own client.
"""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from PIL import Image

from app.tasks import media_tasks

CID = uuid.uuid4()
UPLOADER = uuid.uuid4()
MID = uuid.uuid4()


def _media():
    return MagicMock(
        community_id=CID,
        uploader_id=UPLOADER,
        storage_key="k",
        size_bytes=3,
    )


def _session_factory():
    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=cm)


def _assert_invalidated(inv, redis, create):
    create.assert_called_once()
    inv.assert_awaited_once()
    assert inv.await_args.args == (CID,)
    kw = inv.await_args.kwargs
    assert kw["service"] == "media"
    assert kw["action"] == "ready"
    assert kw["user_id"] == UPLOADER
    assert kw["client"] is create.return_value
    create.return_value.aclose.assert_awaited_once()


async def test_thumbnail_ready_invalidates_with_own_client():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, format="PNG")
    storage = AsyncMock()
    storage.get.return_value = buf.getvalue()
    repo = AsyncMock()
    repo.get.return_value = _media()
    with (
        patch.object(media_tasks, "async_session_factory", _session_factory()),
        patch.object(media_tasks, "MediaRepository", return_value=repo),
        patch.object(media_tasks, "get_storage_backend", return_value=storage),
        patch.object(media_tasks, "create_pool", return_value=AsyncMock()) as create,
        patch.object(media_tasks, "invalidate_search_cache_for_community", new=AsyncMock()) as inv,
    ):
        result = await media_tasks._generate_thumbnail_async(MID)
    assert result == {"status": "processed"}
    _assert_invalidated(inv, None, create)


async def test_transcode_ready_invalidates_with_own_client():
    storage = AsyncMock()
    storage.get.return_value = b"raw"
    repo = AsyncMock()
    repo.get.return_value = _media()

    def fake_run(cmd, **_kw):
        with open(cmd[-1], "wb") as f:
            f.write(b"out")

    def fake_thumb(_src, dst):
        Image.new("RGB", (4, 4)).save(dst, format="JPEG")

    with (
        patch.object(media_tasks, "async_session_factory", _session_factory()),
        patch.object(media_tasks, "MediaRepository", return_value=repo),
        patch.object(media_tasks, "get_storage_backend", return_value=storage),
        patch.object(media_tasks, "probe_and_set_encoder", return_value="libx264"),
        patch.object(media_tasks, "build_ffmpeg_command", lambda i, o, e: ["ffmpeg", o]),
        patch.object(media_tasks, "extract_video_metadata", return_value={"width": 1}),
        patch.object(media_tasks, "extract_thumbnail", fake_thumb),
        patch.object(media_tasks, "decrement_storage_used", new=AsyncMock()),
        patch.object(media_tasks, "increment_storage_used", new=AsyncMock()),
        patch("subprocess.run", fake_run),
        patch.object(media_tasks, "create_pool", return_value=AsyncMock()) as create,
        patch.object(media_tasks, "invalidate_search_cache_for_community", new=AsyncMock()) as inv,
    ):
        result = await media_tasks._transcode_video_async(str(MID))
    assert result == {"status": "processed"}
    _assert_invalidated(inv, None, create)
