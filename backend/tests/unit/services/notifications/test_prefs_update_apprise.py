"""
@file test_prefs_update_apprise.py
@brief PATCH /preferences: apprise values must be bool per type (400 otherwise).
"""

import pytest

from app.core.exceptions import AppError
from app.schemas.notification import NotificationPreferencesUpdate
from app.services.notifications.api_helpers import build_prefs_update


def test_apprise_bool_merges():
    patch = NotificationPreferencesUpdate(notification_prefs={"mention": {"apprise": True}})
    out = build_prefs_update(patch, {"mention": {"push": True, "apprise": False}})
    assert out["notification_prefs"]["mention"] == {"push": True, "apprise": True}


@pytest.mark.parametrize("bad", ["yes", 1, None, "true"])
def test_apprise_non_bool_rejected(bad):
    patch = NotificationPreferencesUpdate(notification_prefs={"mention": {"apprise": bad}})
    with pytest.raises(AppError) as ei:
        build_prefs_update(patch, {})
    assert ei.value.code == "NOTIF_PREF_INVALID"
