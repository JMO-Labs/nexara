"""@file Exports the global list field-type registry singleton."""

from app.services.list_field_registry import FieldTypeNotFound, ListFieldRegistry
from app.services.list_field_types.base import FieldType, FieldTypeBase
from app.services.list_field_types.base_types import BUILTIN_TYPES
from app.services.list_field_types.builtin import DateField, LocationField

registry = ListFieldRegistry()
for _ft in [*BUILTIN_TYPES, DateField(), LocationField()]:
    registry.register(_ft)

__all__ = ["FieldType", "FieldTypeBase", "FieldTypeNotFound", "ListFieldRegistry", "registry"]
