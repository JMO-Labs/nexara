"""
@file test_settings_privacy_schema.py
@brief Privacy and appearance fields on the user settings schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.settings import UserSettingsResponse, UserSettingsUpdate


def test_update_accepts_privacy_and_appearance_fields() -> None:
    data = UserSettingsUpdate(
        profile_visible_to="admin_only",
        show_online_status=False,
        show_last_seen=False,
        show_birthday_to="nobody",
        show_birthday_year=True,
        allow_sassybot=False,
        font_size="large",
        compact_feed=True,
    )
    assert data.model_dump(exclude_unset=True)["font_size"] == "large"


@pytest.mark.parametrize(
    "field,value",
    [
        ("profile_visible_to", "nobody"),
        ("show_birthday_to", "everyone"),
        ("font_size", "huge"),
    ],
)
def test_update_rejects_invalid_enum(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        UserSettingsUpdate(**{field: value})


def test_response_exposes_new_fields() -> None:
    fields = UserSettingsResponse.model_fields
    for name in (
        "profile_visible_to",
        "show_online_status",
        "show_last_seen",
        "show_birthday_to",
        "show_birthday_year",
        "allow_sassybot",
        "font_size",
        "compact_feed",
    ):
        assert name in fields
