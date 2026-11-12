"""@file Tests for special list field types (signup, user_pull)."""

import pytest
from pydantic import ValidationError

from app.services.list_field_types import registry


def test_registered():
    assert {"signup", "user_pull"} <= set(registry.keys())
    assert registry.get("signup").key == "signup"
    assert registry.get("user_pull").key == "user_pull"


def test_signup_validate_and_project():
    ft = registry.get("signup")
    cfg = {"default_quantity_needed": 3}
    assert ft.validate_value(2, cfg) == 2
    for bad in (0, -1, "2", 1.5, True):
        with pytest.raises(ValueError):
            ft.validate_value(bad, cfg)
    assert ft.project_columns(2, cfg) == {"signup_quantity_needed": 3}
    assert ft.validate_config(cfg) == cfg
    assert ft.serialize(2) == 2
    assert ft.deserialize(2) == 2


def test_signup_config_rejects_zero():
    with pytest.raises(ValidationError):
        registry.get("signup").validate_config({"default_quantity_needed": 0})


def test_user_pull_config():
    ft = registry.get("user_pull")
    cfg = ft.validate_config({"pull_from": "email"})
    assert cfg == {"pull_from": "email", "target_user_field": None}
    cfg = ft.validate_config({"pull_from": "phone", "target_user_field": "mobile"})
    assert cfg["target_user_field"] == "mobile"
    with pytest.raises(ValidationError):
        ft.validate_config({"pull_from": "ssn"})


def test_user_pull_values():
    ft = registry.get("user_pull")
    cfg = {"pull_from": "email"}
    assert ft.validate_value("anything", cfg) == "anything"
    assert ft.project_columns("x", cfg) == {}
    assert ft.serialize("x") is None
    assert ft.deserialize("x") is None
