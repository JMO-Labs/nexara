"""@file Tests for the list field-type registry."""

import pytest
from pydantic import BaseModel

from app.services.list_field_registry import FieldTypeNotFoundError, ListFieldRegistry
from app.services.list_field_types import registry
from app.services.list_field_types.base import FieldType, FieldTypeBase


class _Cfg(BaseModel):
    max: int = 5


class _Num(FieldTypeBase):
    key = "num"
    label = "Number"
    config_model = _Cfg

    def validate_value(self, value, config):
        if value > config.get("max", 5):
            raise ValueError("too big")
        return value

    def project_columns(self, value, config):
        return {"value_number": value}


def test_singleton():
    assert ListFieldRegistry() is ListFieldRegistry()
    assert registry is ListFieldRegistry()


def test_register_get_keys():
    registry.register(_Num())
    assert "num" in registry.keys()
    ft = registry.get("num")
    assert isinstance(ft, FieldType)


def test_unknown_raises():
    with pytest.raises(FieldTypeNotFoundError):
        registry.get("nope")
    assert issubclass(FieldTypeNotFoundError, KeyError)


def test_delegation():
    registry.register(_Num())
    assert registry.validate_value("num", 3, {}) == 3
    with pytest.raises(ValueError):
        registry.validate_value("num", 9, {"max": 5})
    assert registry.validate_config("num", {"max": 2}) == {"max": 2}
    assert registry.project_columns("num", 4, {}) == {"value_number": 4}


def test_base_defaults():
    b = FieldTypeBase()
    assert b.validate_value("x", {}) == "x"
    assert b.project_columns("x", {}) == {}
    assert b.serialize("x") == "x"
    assert b.deserialize("x") == "x"
