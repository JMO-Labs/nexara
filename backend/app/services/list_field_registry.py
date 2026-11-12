"""@file Singleton registry of list field types."""

from typing import TYPE_CHECKING, Any, ClassVar, Optional

if TYPE_CHECKING:
    from app.services.list_field_types.base import FieldType


class FieldTypeNotFound(KeyError):
    """@brief Raised when a field type key is not registered."""


class ListFieldRegistry:
    """@brief In-process singleton mapping key -> FieldType."""

    _instance: ClassVar[Optional["ListFieldRegistry"]] = None
    _types: dict[str, "FieldType"]

    def __new__(cls) -> "ListFieldRegistry":
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._types = {}
            cls._instance = inst
        return cls._instance

    def register(self, field_type: "FieldType") -> None:
        """@brief Store a field type by its key (replaces existing)."""
        self._types[field_type.key] = field_type

    def get(self, key: str) -> "FieldType":
        """@brief Return the field type or raise FieldTypeNotFound."""
        try:
            return self._types[key]
        except KeyError:
            raise FieldTypeNotFound(key) from None

    def keys(self) -> list[str]:
        """@brief List registered keys."""
        return list(self._types)

    def validate_value(self, key: str, value: Any, config: dict[str, Any]) -> Any:
        """@brief Delegate value validation."""
        return self.get(key).validate_value(value, config)

    def validate_config(self, key: str, config: dict[str, Any]) -> dict[str, Any]:
        """@brief Delegate config validation."""
        return self.get(key).validate_config(config)

    def project_columns(self, key: str, value: Any, config: dict[str, Any]) -> dict[str, Any]:
        """@brief Delegate typed-column projection."""
        return self.get(key).project_columns(value, config)
