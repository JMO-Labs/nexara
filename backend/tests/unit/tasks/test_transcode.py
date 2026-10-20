"""
@file test_transcode.py
@brief Unit tests for video transcoding module.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.transcode import (
    ALLOWED_VIDEO_TYPES,
    MAX_VIDEO_SIZE,
    build_ffmpeg_command,
    extract_thumbnail,
    probe_and_set_encoder,
)


class TestBuildFfmpegCommand:
    def test_software_encoder(self):
        cmd = build_ffmpeg_command("/tmp/in.mp4", "/tmp/out.mp4", "libx264")
        assert "-i" in cmd
        assert "/tmp/in.mp4" in cmd
        assert "-c:v" in cmd
        assert "libx264" in cmd
        assert "-movflags" in cmd
        assert "+faststart" in cmd

    def test_nvidia_encoder(self):
        cmd = build_ffmpeg_command("/tmp/in.mp4", "/tmp/out.mp4", "h264_nvenc")
        assert "h264_nvenc" in cmd

    def test_output_path_last(self):
        cmd = build_ffmpeg_command("/tmp/in.mp4", "/tmp/out.mp4", "libx264")
        assert cmd[-1] == "/tmp/out.mp4"


class TestProbeAndSetEncoder:
    def test_default_software(self):
        encoder = probe_and_set_encoder("none")
        assert encoder == "libx264"

    def test_nvidia_when_available(self):
        with patch("app.core.transcode.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            encoder = probe_and_set_encoder("nvidia")
            assert encoder == "h264_nvenc"

    def test_nvidia_fallback_on_failure(self):
        with patch("app.core.transcode.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("GPU not available")
            encoder = probe_and_set_encoder("nvidia")
            assert encoder == "libx264"


class TestExtractThumbnail:
    def test_calls_ffmpeg(self):
        with patch("app.core.transcode.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            extract_thumbnail("/tmp/video.mp4", "/tmp/thumb.jpg")
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "ffmpeg" in args[0]
            assert "/tmp/video.mp4" in args


class TestConstants:
    def test_allowed_video_types(self):
        assert "video/mp4" in ALLOWED_VIDEO_TYPES
        assert "video/quicktime" in ALLOWED_VIDEO_TYPES
        assert "video/webm" in ALLOWED_VIDEO_TYPES

    def test_max_video_size(self):
        assert MAX_VIDEO_SIZE == 500 * 1024 * 1024
