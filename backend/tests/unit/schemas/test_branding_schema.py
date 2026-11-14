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


@pytest.mark.parametrize(
    ("field", "limit"),
    [("email_footer_text", 300), ("email_sender_name", 100), ("landing_cta_text", 200)],
)
def test_text_fields_enforce_max_length(field: str, limit: int) -> None:
    """@brief Branding text fields reject values over their ticket limits."""
    BrandingUpdate(**{field: "x" * limit})
    with pytest.raises(ValidationError):
        BrandingUpdate(**{field: "x" * (limit + 1)})
