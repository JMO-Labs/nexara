"""@file Tests for the in-process NotificationType registry."""

import dataclasses

import pytest

from app.services.notifications import (
    Action,
    NotificationPayload,
    NotificationType,
    get,
    iter_types,
    register,
    registry,
    to_json_schema,
)


@pytest.fixture(autouse=True)
def clean_registry():
    saved = dict(registry._REGISTRY)
    registry._REGISTRY.clear()
    yield
    registry._REGISTRY.clear()
    registry._REGISTRY.update(saved)


def _make(key: str = "post.liked", **kw) -> NotificationType:
    return NotificationType(
        key=key,
        category="social",
        payload_schema=NotificationPayload,
        default_channels={"inapp": True, "email": False},
        **kw,
    )


def test_register_and_get():
    t = _make()
    register(t)
    assert get("post.liked") is t


def test_get_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        get("nope")


def test_duplicate_register_raises():
    register(_make())
    with pytest.raises(ValueError):
        register(_make())


def test_iter_types_returns_list_of_all():
    a, b = _make("a.one"), _make("b.two")
    register(a)
    register(b)
    assert iter_types() == [a, b]


def test_type_is_frozen_with_defaults():
    t = _make()
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.key = "x"  # type: ignore[misc]
    assert t.user_configurable == ("inapp", "email", "push", "toast", "apprise")
    assert t.group_window_seconds is None
    assert t.toast_on_arrival is False
    assert t.bypass_dnd is False
    assert t.digestable is True
    assert t.actions == ()
    assert t.icon == "inbox"
    assert t.plugin_id is None
    assert len(dataclasses.fields(NotificationType)) >= 13


def test_action_defaults_and_frozen():
    a = Action("ok", "k.ok", "POST", "/x/{id}")
    assert a.style == "neutral"
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.key = "y"  # type: ignore[misc]


def test_payload_defaults():
    p = NotificationPayload(message="hi")
    assert p.link is None and p.actor_id is None and p.target_id is None


def test_to_json_schema():
    register(_make(actions=(Action("ok", "k.ok", "POST", "/x"),), plugin_id="p"))
    out = to_json_schema()
    assert len(out) == 1
    d = out[0]
    assert d["key"] == "post.liked"
    assert d["category"] == "social"
    assert d["default_channels"] == {"inapp": True, "email": False}
    assert d["actions"][0]["key"] == "ok"
    assert d["plugin_id"] == "p"
    assert d["payload_schema"]["properties"]["message"]["type"] == "string"
