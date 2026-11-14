"""
@file test_notification_list_types.py
@brief PREF_MAP coverage and defaults for list notification types.
"""

from __future__ import annotations

import pytest

from app.models.user_settings import UserSettings
from app.services.notification_service import PREF_MAP

DEFAULTS = {
    "list.item": (True, False),
    "list.signup": (True, False),
    "list.completed": (True, False),
    "list.expiring": (True, True),
    "list.member": (True, True),
}


@pytest.mark.parametrize("type_key", sorted(DEFAULTS))
def test_pref_map_has_list_type(type_key: str) -> None:
    key = type_key.split(".")[1]
    assert PREF_MAP[type_key] == (f"notif_list_{key}_inapp", f"notif_list_{key}_email")


@pytest.mark.parametrize("type_key", sorted(DEFAULTS))
def test_user_settings_columns_and_defaults(type_key: str) -> None:
    inapp_col, email_col = PREF_MAP[type_key]
    table = UserSettings.__table__
    for col, expected in zip((inapp_col, email_col), DEFAULTS[type_key], strict=True):
        default = table.c[col].server_default.arg
        assert str(default).lower() == str(expected).lower()
