"""
@file transcode.py
@brief Video transcoding utilities using ffmpeg.

Probes GPU availability, builds ffmpeg commands for H.264/AAC output,
extracts metadata and thumbnails from video files.
"""

from __future__ import annotations

import json
import os
import subprocess

ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
"""@brief MIME types accepted for video uploads."""

MAX_VIDEO_SIZE = 500 * 1024 * 1024
"""@brief Maximum video upload size in bytes (500 MB)."""

ENCODER_PROFILES: dict[str, list[str]] = {
    "libx264": ["-preset", "medium", "-crf", "23"],
    "h264_nvenc": ["-preset", "p4", "-rc", "vbr", "-cq", "23"],
    "h264_vaapi": ["-qp", "23"],
}
"""@brief FFmpeg encoder-specific arguments (for reference)."""


def probe_and_set_encoder(hw_accel: str = "none") -> str:
    """
    @brief Probe GPU availability and return encoder name.

    Checks TRANSCODE_HW_ACCEL env var (none/nvidia/vaapi). For nvidia:
    tries h264_nvenc; for vaapi: tries h264_vaapi. Falls back to libx264
    on failure or when hw_accel is none.

    @param hw_accel Override: "none", "nvidia", or "vaapi".
    @return Encoder name (libx264, h264_nvenc, or h264_vaapi).
    """
    accel = os.environ.get("TRANSCODE_HW_ACCEL", "none")
    if hw_accel != "none":
        accel = hw_accel
    if accel == "none":
        return "libx264"
    if accel == "nvidia":
        try:
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            return "h264_nvenc"
        except (subprocess.CalledProcessError, FileNotFoundError, Exception):
            return "libx264"
    if accel == "vaapi":
        try:
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            return "h264_vaapi"
        except (subprocess.CalledProcessError, FileNotFoundError, Exception):
            return "libx264"
    return "libx264"


def build_ffmpeg_command(
    input_path: str,
    output_path: str,
    encoder: str,
) -> list[str]:
    """
    @brief Build ffmpeg command for H.264+AAC, max 1920x1080, faststart.

    @param input_path Path to input video file.
    @param output_path Path to output MP4 file.
    @param encoder Video encoder (libx264, h264_nvenc, h264_vaapi).
    @return List of command-line arguments for subprocess.
    """
    scale = "scale='min(1920,iw)':'min(1080,ih)':force_original_aspect_ratio=decrease"
    return [
        "ffmpeg",
        "-i",
        input_path,
        "-c:v",
        encoder,
        "-preset",
        "medium",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-vf",
        scale,
        "-movflags",
        "+faststart",
        "-y",
        output_path,
    ]


def extract_video_metadata(file_path: str) -> dict[str, float]:
    """
    @brief Run ffprobe and extract width, height, duration_secs.

    @param file_path Path to video file.
    @return Dict with width, height, duration_secs (float).
    """
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            file_path,
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    data = json.loads(result.stdout)
    out: dict[str, float] = {"width": 0, "height": 0, "duration_secs": 0.0}
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            out["width"] = int(stream.get("width", 0) or 0)
            out["height"] = int(stream.get("height", 0) or 0)
            break
    fmt = data.get("format", {})
    dur = fmt.get("duration")
    if dur is not None:
        out["duration_secs"] = float(dur)
    return out


def extract_thumbnail(input_path: str, output_path: str) -> None:
    """
    @brief Extract first frame as JPEG via ffmpeg.

    @param input_path Path to input video.
    @param output_path Path to output thumbnail image.
    """
    subprocess.run(
        [
            "ffmpeg",
            "-i",
            input_path,
            "-vframes",
            "1",
            "-f",
            "image2",
            "-y",
            output_path,
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )
