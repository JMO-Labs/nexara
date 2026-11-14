"""@file Tests for effective_channels preference resolution."""

from app.services.notifications import NotificationPayload, NotificationType
from app.services.notifications.prefs import effective_channels

ALL = {"inapp", "email", "push", "toast", "apprise"}


def _type(**kw) -> NotificationType:
    base = dict(
        key="mention",
        category="social",
        payload_schema=NotificationPayload,
        default_channels={"inapp": True, "email": True},
    )
    base.update(kw)
    return NotificationType(**base)


def test_no_overrides_returns_defaults_with_all_channels():
    out = effective_channels(_type(), {})
    assert set(out) == ALL
    assert out == {
        "inapp": True,
        "email": True,
        "push": False,
        "toast": False,
        "apprise": False,
    }


def test_none_override_entry_returns_defaults():
    assert effective_channels(_type(), {"mention": None})["email"] is True


def test_user_overrides_merge():
    out = effective_channels(_type(), {"mention": {"email": False, "push": 1}})
    assert out["email"] is False
    assert out["push"] is True
    assert out["inapp"] is True


def test_unknown_keys_ignored():
    out = effective_channels(_type(), {"other": {"email": False}, "mention": {"sms": True}})
    assert set(out) == ALL
    assert out["email"] is True


def test_user_configurable_filtering():
    t = _type(user_configurable=("push",))
    out = effective_channels(t, {"mention": {"email": False, "push": True}})
    assert out["email"] is True
    assert out["push"] is True


def test_system_type_allows_no_overrides():
    t = _type(user_configurable=())
    out = effective_channels(t, {"mention": {"inapp": False}})
    assert out["inapp"] is True


def test_does_not_mutate_defaults():
    t = _type()
    effective_channels(t, {"mention": {"email": False}})
    assert t.default_channels == {"inapp": True, "email": True}


def test_apprise_defaults_off_and_is_user_configurable():
    t = _type()
    assert "apprise" in t.user_configurable
    assert effective_channels(t, {})["apprise"] is False
    assert effective_channels(t, {"mention": {"apprise": True}})["apprise"] is True
