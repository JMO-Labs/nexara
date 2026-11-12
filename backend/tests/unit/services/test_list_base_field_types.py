"""@file Tests for base list field types."""

import pytest

from app.services.list_field_types import registry

OPTS = {"options": [{"value": "a", "label": "A"}, {"value": "b", "label": "B"}]}

CASES = [
    ("bool", {}, [True, False], ["x", 1, None]),
    ("text", {"multiline": False}, ["hi", None], [5, ["a"]]),
    ("select", OPTS, ["a"], ["z", 1]),
    ("multiselect", OPTS, [["a", "b"], []], [["z"], "a", ["a", 1]]),
    ("time", {}, ["09:30", "23:59", "00:00"], ["24:00", "9:30", "12:60", "x", 5]),
    ("checkbox", {"completion_mode": "shared"}, [True, False], ["x", 1]),
]


def test_all_registered():
    for key, *_ in CASES:
        assert key in registry.keys()


@pytest.mark.parametrize(("key", "cfg", "good", "bad"), CASES)
def test_validation(key, cfg, good, bad):
    for v in good:
        assert registry.validate_value(key, v, cfg) == v
    for v in bad:
        with pytest.raises(ValueError):
            registry.validate_value(key, v, cfg)


def test_checkbox_config_rejects_bad_mode():
    with pytest.raises(ValueError):
        registry.validate_config("checkbox", {"completion_mode": "nope"})


def test_select_config_normalizes():
    assert registry.validate_config("select", OPTS) == OPTS
