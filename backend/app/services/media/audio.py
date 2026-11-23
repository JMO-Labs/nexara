"""
@file audio.py
@brief Audio upload rules: allowed types, 25 MB cap, magic-byte check.

Kept apart from ``media_service`` (file-length budget). Voice recordings are
transcoded to AAC ``.m4a`` by ``transcode_audio`` after upload.
"""

from __future__ import annotations

from app.core.exceptions import AppError
from app.core.i18n import _
from app.services.storage.validation import (
    UploadValidationError,
    validate_file_content,
    validate_file_size,
)

ALLOWED_AUDIO_TYPES = {"audio/mpeg", "audio/mp4", "audio/ogg", "audio/webm"}
"""@brief MIME types accepted for audio uploads (m4a/mp3/ogg/opus/webm)."""

AUDIO_EXT = {"audio/mpeg": "mp3", "audio/mp4": "m4a", "audio/ogg": "ogg", "audio/webm": "webm"}
"""@brief Storage extension per audio MIME type."""


def audio_base_type(content_type: str) -> str | None:
    """
    @brief Strip parameters (``audio/webm;codecs=opus``) and test membership.
    @param content_type Client-declared MIME type.
    @return The bare audio type, or None when it is not an accepted audio type.
    """
    base = content_type.split(";")[0].strip().lower()
    return base if base in ALLOWED_AUDIO_TYPES else None


def check_audio_upload(file_data: bytes, declared: str, size: int) -> str:
    """
    @brief Validate size, length consistency and magic bytes of an audio upload.
    @param file_data Raw bytes.
    @param declared Bare declared audio type.
    @param size Declared size in bytes.
    @return Detected MIME type (what is stored).
    @raises AppError FILE_TOO_LARGE (413), FILE_SIZE_MISMATCH or INVALID_FILE_TYPE (400).
    """
    try:
        validate_file_size(size, declared)
    except UploadValidationError as exc:
        raise AppError("FILE_TOO_LARGE", _("Audio must be 25 MB or smaller."), 413) from exc
    if len(file_data) != size:
        raise AppError("FILE_SIZE_MISMATCH", _("File size mismatch."), 400)
    try:
        detected = validate_file_content(file_data[:16], declared)
    except UploadValidationError:
        detected = ""
    if detected not in ALLOWED_AUDIO_TYPES:
        raise AppError("INVALID_FILE_TYPE", _("That is not a supported audio file."), 400)
    return detected
