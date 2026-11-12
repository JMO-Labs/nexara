"""
@file test_branding_contrast.py
@brief Unit tests for accent_passes_aa in app.services.branding.contrast.
"""

from __future__ import annotations

import pytest

from app.services.branding.contrast import accent_passes_aa


@pytest.mark.parametrize("value", ["8b5cf6", "#fff", "#GGGGGG", "", "#1234567"])
def test_accent_passes_aa_rejects_invalid_hex(value: str) -> None:
    assert accent_passes_aa(value) is False


def test_accent_passes_aa_accepts_light_accent() -> None:
    assert accent_passes_aa("#FFFFFF") is True


def test_accent_passes_aa_rejects_dark_accent() -> None:
    assert accent_passes_aa("#14301E") is False
