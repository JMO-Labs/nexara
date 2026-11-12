"""
@file test_branding_schema.py
@brief Accent contrast validation on BrandingUpdate.
"""

import pytest
from pydantic import ValidationError

from app.schemas.branding import BrandingUpdate


def test_accent_accepts_light_color() -> None:
    assert BrandingUpdate(color_accent="#C6B4F5").color_accent == "#C6B4F5"


def test_accent_rejects_low_contrast() -> None:
    with pytest.raises(ValidationError):
        BrandingUpdate(color_accent="#14301E")
