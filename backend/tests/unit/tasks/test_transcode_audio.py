"""
@file test_transcode_audio.py
@brief transcode_audio with ffmpeg/ffprobe mocked: duration set, >15 min rejected.
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from app.tasks import audio_tasks


def _run(duration_in: float, duration_out: float = 61.5):
    media = MagicMock(
        storage_key="originals/x.webm", size_bytes=100, uploader_id=uuid.uuid4(),
        community_id=uuid.uuid4(), content_type="audio/webm",
    )  # fmt: skip
    repo = MagicMock()
    repo.get = AsyncMock(return_value=media)
    repo.update_status = AsyncMock()
    storage = MagicMock(get=AsyncMock(return_value=b"raw"), put=AsyncMock(), delete=AsyncMock())
    session = AsyncMock()

    @asynccontextmanager
    async def factory():
        yield session

    def fake_ffmpeg(cmd, **_kw):
        with open(cmd[-1], "wb") as f:
            f.write(b"m4a-bytes")

    durations = iter([duration_in, duration_out])
    patches = (
        patch.object(audio_tasks, "async_session_factory", factory),
        patch.object(audio_tasks, "MediaRepository", return_value=repo),
        patch.object(audio_tasks, "get_storage_backend", return_value=storage),
        patch.object(audio_tasks, "probe_duration", side_effect=lambda _p: next(durations)),
        patch.object(audio_tasks.subprocess, "run", side_effect=fake_ffmpeg),
        patch.object(audio_tasks, "decrement_storage_used", AsyncMock()),
        patch.object(audio_tasks, "increment_storage_used", AsyncMock()),
        patch.object(audio_tasks, "_invalidate_ready", AsyncMock()),
    )
    return media, repo, storage, patches


async def test_sets_duration_and_stores_m4a():
    media, repo, storage, patches = _run(61.5)
    for p in patches:
        p.start()
    try:
        out = await audio_tasks._transcode_audio_async(str(uuid.uuid4()))
    finally:
        patch.stopall()
    assert out == {"status": "processed"}
    status = repo.update_status.await_args
    assert status.args[1] == "ready" and status.kwargs["duration_secs"] == 61.5
    assert storage.put.await_args.args[1] == b"m4a-bytes"
    assert media.content_type == "audio/mp4"


async def test_sixteen_minutes_is_rejected_without_transcoding():
    _media, repo, storage, patches = _run(16 * 60)
    for p in patches:
        p.start()
    try:
        out = await audio_tasks._transcode_audio_async(str(uuid.uuid4()))
        ran = audio_tasks.subprocess.run.called
    finally:
        patch.stopall()
    assert out == {"status": "rejected"}
    assert repo.update_status.await_args.args[1] == "rejected"
    assert not ran
    storage.put.assert_not_awaited()


def test_command_is_aac_96k_m4a():
    cmd = audio_tasks.build_audio_command("in", "out.m4a")
    assert "aac" in cmd and "96k" in cmd and "-vn" in cmd and cmd[-1] == "out.m4a"
