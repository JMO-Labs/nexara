"""@file Built-in base list field types (bool, text, select, multiselect, time, checkbox)."""

import re
from typing import Any, Literal

from pydantic import BaseModel

from app.services.list_field_types.base import FieldTypeBase

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class EmptyConfig(BaseModel):
    """@brief Config with no options."""


class TextConfig(BaseModel):
    """@brief Text field config."""

    multiline: bool = False


class SelectOption(BaseModel):
    """@brief One selectable option."""

    value: str
    label: str


class OptionsConfig(BaseModel):
    """@brief Config holding select options."""

    options: list[SelectOption] = []


class CheckboxConfig(BaseModel):
    """@brief Checkbox config."""

    completion_mode: Literal["shared", "per_user"] = "shared"


def _values(config: dict[str, Any]) -> list[Any]:
    return [o["value"] for o in config.get("options", [])]


def _require_bool(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError("value must be a boolean")
    return value


class BoolField(FieldTypeBase):
    """@brief Boolean field."""

    key = "bool"
    label = "Boolean"
    config_model = EmptyConfig

    def validate_value(self, value: Any, config: dict[str, Any]) -> Any:
        """@brief Require a bool."""
        return _require_bool(value)


class TextField(FieldTypeBase):
    """@brief Text field."""

    key = "text"
    label = "Text"
    config_model = TextConfig

    def validate_value(self, value: Any, config: dict[str, Any]) -> Any:
        """@brief Require str or None."""
        if value is not None and not isinstance(value, str):
            raise ValueError("value must be a string")
        return value


class SelectField(FieldTypeBase):
    """@brief Single-select field."""

    key = "select"
    label = "Select"
    config_model = OptionsConfig

    def validate_value(self, value: Any, config: dict[str, Any]) -> Any:
        """@brief Require value among configured options."""
        if value not in _values(config):
            raise ValueError("value not in options")
        return value


class MultiSelectField(FieldTypeBase):
    """@brief Multi-select field."""

    key = "multiselect"
    label = "Multi-select"
    config_model = OptionsConfig

    def validate_value(self, value: Any, config: dict[str, Any]) -> Any:
        """@brief Require list whose items are all configured options."""
        if not isinstance(value, list):
            raise ValueError("value must be a list")
        allowed = _values(config)
        if any(v not in allowed for v in value):
            raise ValueError("value not in options")
        return value


class TimeField(FieldTypeBase):
    """@brief Time-of-day (HH:MM) field."""

    key = "time"
    label = "Time"
    config_model = EmptyConfig

    def validate_value(self, value: Any, config: dict[str, Any]) -> Any:
        """@brief Require HH:MM string."""
        if not isinstance(value, str) or not _TIME_RE.match(value):
            raise ValueError("value must be HH:MM")
        return value


class CheckboxField(FieldTypeBase):
    """@brief Checkbox field with shared or per-user completion."""

    key = "checkbox"
    label = "Checkbox"
    config_model = CheckboxConfig

    def validate_value(self, value: Any, config: dict[str, Any]) -> Any:
        """@brief Require a bool."""
        return _require_bool(value)


BUILTIN_TYPES: list[FieldTypeBase] = [
    BoolField(),
    TextField(),
    SelectField(),
    MultiSelectField(),
    TimeField(),
    CheckboxField(),
]
