"""
@file test_validation.py
@brief Unit tests for upload magic byte validation.

Verifies that each supported file type is correctly identified from
its magic bytes, and that unsupported/malicious types are rejected.
"""

import pytest

from app.services.storage.validation import (
    UploadValidationError,
    validate_file_content,
    validate_file_size,
)


class TestJPEG:
    """@brief Verify JPEG detection."""

    def test_valid_jpeg(self):
        header = b"\xff\xd8\xff\xe0" + b"\x00" * 8
        assert validate_file_content(header) == "image/jpeg"

    def test_jpeg_exif(self):
        header = b"\xff\xd8\xff\xe1" + b"\x00" * 8
        assert validate_file_content(header) == "image/jpeg"


class TestPNG:
    """@brief Verify PNG detection."""

    def test_valid_png(self):
        header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4
        assert validate_file_content(header) == "image/png"


class TestGIF:
    """@brief Verify GIF87a and GIF89a detection."""

    def test_gif87a(self):
        header = b"GIF87a" + b"\x00" * 6
        assert validate_file_content(header) == "image/gif"

    def test_gif89a(self):
        header = b"GIF89a" + b"\x00" * 6
        assert validate_file_content(header) == "image/gif"


class TestWebP:
    """@brief Verify WebP detection (RIFF....WEBP)."""

    def test_valid_webp(self):
        header = b"RIFF\x00\x00\x00\x00WEBP"
        assert validate_file_content(header) == "image/webp"

    def test_riff_but_not_webp(self):
        header = b"RIFF\x00\x00\x00\x00AVI "
        with pytest.raises(UploadValidationError, match="Unsupported"):
            validate_file_content(header)


class TestMP4:
    """@brief Verify MP4/ISO Base Media Format detection."""

    def test_isom_brand(self):
        header = b"\x00\x00\x00\x20ftypiso2" + b"\x00" * 4
        assert validate_file_content(header) == "video/mp4"

    def test_mp41_brand(self):
        header = b"\x00\x00\x00\x20ftypmp41" + b"\x00" * 4
        assert validate_file_content(header) == "video/mp4"


class TestMOV:
    """@brief Verify QuickTime/MOV detection."""

    def test_quicktime_brand(self):
        header = b"\x00\x00\x00\x14ftypqt  "
        assert validate_file_content(header) == "video/quicktime"


class TestWebM:
    """@brief Verify WebM/Matroska detection."""

    def test_valid_webm(self):
        header = b"\x1a\x45\xdf\xa3" + b"\x00" * 8
        assert validate_file_content(header) == "video/webm"


class TestSVGRejection:
    """@brief SVG files must always be rejected."""

    def test_svg_tag(self):
        header = b"<svg xmlns" + b"\x00" * 2
        with pytest.raises(UploadValidationError, match="SVG"):
            validate_file_content(header)

    def test_xml_prolog(self):
        header = b"<?xml version" + b"\x00" * 2
        with pytest.raises(UploadValidationError, match="SVG"):
            validate_file_content(header)

    def test_svg_with_whitespace(self):
        header = b"  \n  <svg" + b"\x00" * 4
        with pytest.raises(UploadValidationError, match="SVG"):
            validate_file_content(header)


class TestUnsupportedTypes:
    """@brief Unknown file types must be rejected."""

    def test_random_bytes(self):
        with pytest.raises(UploadValidationError, match="Unsupported"):
            validate_file_content(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b")

    def test_too_small(self):
        with pytest.raises(UploadValidationError, match="too small"):
            validate_file_content(b"\x00\x01")


class TestFileSizeValidation:
    """@brief Verify file size limit enforcement."""

    def test_image_within_limit(self):
        validate_file_size(10 * 1024 * 1024, "image/jpeg")

    def test_image_exceeds_limit(self):
        with pytest.raises(UploadValidationError, match="exceeds"):
            validate_file_size(25 * 1024 * 1024, "image/jpeg")

    def test_video_within_limit(self):
        validate_file_size(100 * 1024 * 1024, "video/mp4")

    def test_video_exceeds_limit(self):
        with pytest.raises(UploadValidationError, match="exceeds"):
            validate_file_size(600 * 1024 * 1024, "video/mp4")

    def test_unknown_category_rejected(self):
        with pytest.raises(UploadValidationError, match="Unsupported content category"):
            validate_file_size(100, "application/pdf")
