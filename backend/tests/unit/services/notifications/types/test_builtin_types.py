"""@file Tests for the 12 built-in notification types."""

from datetime import UTC, datetime

import pytest

import app.services.notifications.types  # noqa: F401  (registers types)
from app.services.notifications import get, iter_types

VALID = {
    "mention": {"actor_name": "A", "excerpt": "x"},
    "comment": {"actor_name": "A", "excerpt": "x"},
    "reaction": {"actor_name": "A", "emoji": "x", "excerpt": "x"},
    "new_post": {"actor_name": "A", "title": "t"},
    "system": {},
    "invite_accepted": {"actor_name": "A"},
    "event_reminder": {"event_title": "E", "starts_at": datetime(2026, 1, 1, tzinfo=UTC)},
    "event_rsvp": {"actor_name": "A", "event_title": "E", "status": "going"},
    "gallery_activity": {"actor_name": "A", "gallery_title": "G", "activity": "added"},
    "gallery_reminder": {"gallery_title": "G"},
    "prompt": {"prompt_title": "P"},
    "prompt_summary": {"response_count": 3},
}
WINDOWS = {"reaction": 600, "comment": 300, "new_post": 900}
TOASTS = {"mention", "system"}


def test_twelve_types_registered() -> None:
    assert set(VALID) <= {t.key for t in iter_types()}
    assert len(VALID) == 12


@pytest.mark.parametrize("key", sorted(VALID))
def test_type_registered_and_payload_validates(key: str) -> None:
    t = get(key)
    p = t.payload_schema.model_validate({"message": "m", **VALID[key]})
    assert p.message == "m"


@pytest.mark.parametrize("key", sorted(VALID))
def test_payload_rejects_missing_fields(key: str) -> None:
    t = get(key)
    if not VALID[key]:
        pytest.skip("base payload only")
    with pytest.raises(ValueError):
        t.payload_schema.model_validate({"message": "m"})


@pytest.mark.parametrize("key", sorted(VALID))
def test_group_window_and_toast(key: str) -> None:
    t = get(key)
    assert t.group_window_seconds == WINDOWS.get(key)
    assert t.toast_on_arrival is (key in TOASTS)
