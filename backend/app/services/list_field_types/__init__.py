"""@file Exports the global list field-type registry singleton."""

from app.services.list_field_registry import FieldTypeNotFound, ListFieldRegistry
from app.services.list_field_types.base import FieldType, FieldTypeBase

from app.services.list_field_types.builtin import DateField, LocationField  # noqa: E402

registry = ListFieldRegistry()
registry.register(DateField())
registry.register(LocationField())

__all__ = ["FieldType", "FieldTypeBase", "FieldTypeNotFound", "ListFieldRegistry", "registry"]
