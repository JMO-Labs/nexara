"""
@file validation.py
@brief Magic byte validation for uploaded files.

Validates actual file content against known magic byte signatures
rather than trusting the client-supplied Content-Type header or
file extension. SVG uploads are always rejected (stored XSS risk).
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


class UploadValidationError(Exception):
    """@brief Raised when an uploaded file fails content validation."""


MAGIC_SIGNATURES: list[tuple[bytes, str, int]] = [
    (b"\xff\xd8\xff", "image/jpeg", 0),
    (b"\x89PNG\r\n\x1a\n", "image/png", 0),
    (b"GIF87a", "image/gif", 0),
    (b"GIF89a", "image/gif", 0),
]
"""@brief (magic_bytes, mime_type, offset) tuples for simple prefix matching."""

WEBP_RIFF_HEADER = b"RIFF"
WEBP_MARKER = b"WEBP"
"""@brief WebP files start with RIFF....WEBP (marker at offset 8)."""

FTYP_BOX_MARKER = b"ftyp"
"""@brief ISO Base Media Format (MP4, MOV) ftyp box marker at offset 4."""

MP4_BRANDS = {b"isom", b"iso2", b"mp41", b"mp42", b"avc1", b"M4V ", b"dash"}
"""@brief ftyp major brands indicating MP4/M4V containers."""

MOV_BRANDS = {b"qt  "}
"""@brief ftyp major brand indicating QuickTime / MOV containers."""

WEBM_HEADER = b"\x1a\x45\xdf\xa3"
"""@brief WebM/Matroska EBML header magic bytes."""

SVG_MARKERS = (b"<svg", b"<?xml")
"""@brief Byte prefixes that indicate SVG content (always rejected)."""

MAX_SIZE_BYTES: dict[str, int] = {
    "image": 20 * 1024 * 1024,
    "video": 500 * 1024 * 1024,
}
"""@brief Per-category upload size limits in bytes."""


def _check_svg(header: bytes) -> bool:
    """@brief Return True if the header looks like SVG content."""
    stripped = header.lstrip()
    for marker in SVG_MARKERS:
        if stripped[: len(marker)].lower() == marker.lower():
            return True
    return False


def _check_webp(header: bytes) -> bool:
    """@brief Return True if the header matches RIFF....WEBP."""
    return len(header) >= 12 and header[:4] == WEBP_RIFF_HEADER and header[8:12] == WEBP_MARKER


def _check_ftyp(header: bytes) -> tuple[bool, str]:
    """
    @brief Check for ISO Base Media Format (MP4/MOV) via ftyp box.

    @return (matched, mime_type) tuple.
    """
    if len(header) < 12:
        return False, ""
    if header[4:8] != FTYP_BOX_MARKER:
        return False, ""
    brand = header[8:12]
    if brand in MP4_BRANDS:
        return True, "video/mp4"
    if brand in MOV_BRANDS:
        return True, "video/quicktime"
    return True, "video/mp4"


def _check_webm(header: bytes) -> bool:
    """@brief Return True if the header matches the EBML/WebM signature."""
    return header[:4] == WEBM_HEADER


def validate_file_content(header: bytes) -> str:
    """
    @brief Detect the true MIME type of a file from its magic bytes.

    Must be called with at least the first 12 bytes of the file.
    SVG content is always rejected regardless of declared type.

    @param header First 12+ bytes of the file.
    @return Detected MIME type string.
    @raises UploadValidationError If the type is unsupported or SVG.
    """
    if len(header) < 4:
        raise UploadValidationError("File too small to identify")

    if _check_svg(header):
        raise UploadValidationError("SVG uploads are not allowed")

    for magic, mime, offset in MAGIC_SIGNATURES:
        end = offset + len(magic)
        if header[offset:end] == magic:
            return mime

    if _check_webp(header):
        return "image/webp"

    matched, mime = _check_ftyp(header)
    if matched:
        return mime

    if _check_webm(header):
        return "video/webm"

    raise UploadValidationError("Unsupported file type")


def validate_file_size(size: int, content_type: str) -> None:
    """
    @brief Verify that the file size is within allowed limits.

    @param size File size in bytes.
    @param content_type MIME type (used to select image vs video limit).
    @raises UploadValidationError If the file exceeds the size limit.
    """
    category = content_type.split("/")[0]
    limit = MAX_SIZE_BYTES.get(category)
    if limit is None:
        raise UploadValidationError(f"Unsupported content category: {category}")
    if size > limit:
        limit_mb = limit / (1024 * 1024)
        raise UploadValidationError(
            f"File size {size} bytes exceeds {category} limit of {limit_mb:.0f}MB"
        )
