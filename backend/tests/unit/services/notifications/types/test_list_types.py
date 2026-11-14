"""@file Tests for list notification types (nexara#358)."""

import pytest

import app.services.notifications.types  # noqa: F401  (registers types)
from app.services.notifications import get
from app.services.notifications.types.list_payloads import item_title

PAYLOADS = {
    "list_item": {"list_id": "l", "item_id": "i", "item_title": "t", "adder_id": "a"},
    "list_completed": {"list_id": "l", "item_id": "i", "item_title": "t", "completer_id": "c"},
    "list_signup": {
        "list_id": "l",
        "item_id": "i",
        "item_title": "t",
        "claimer_id": "c",
        "claimer_name": "C",
        "quantity": 2,
    },
    "list_member": {"list_id": "l", "list_title": "L", "inviter_id": "a", "invitee_id": "b"},
}


@pytest.mark.parametrize("key", sorted(PAYLOADS))
def test_list_type_registered_and_validates(key: str) -> None:
    t = get(key)
    assert t.category == "list"
    p = t.payload_schema.model_validate({"message": "m", **PAYLOADS[key]})
    assert p.message == "m"


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({"title": "Milk", "qty": "2"}, "Milk"),
        ({"name": "Eggs"}, "Eggs"),
        ({"n": 3, "done": True}, ""),
        ({}, ""),
    ],
)
def test_item_title(values: dict[str, object], expected: str) -> None:
    assert item_title(values) == expected
