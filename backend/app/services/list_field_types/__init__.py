"""@file Exports the global list field-type registry singleton."""

from app.services.list_field_registry import FieldTypeNotFound, ListFieldRegistry
from app.services.list_field_types.base import FieldType, FieldTypeBase
from app.services.list_field_types.builtin import BUILTIN_TYPES

registry = ListFieldRegistry()
for _ft in BUILTIN_TYPES:
    registry.register(_ft)

__all__ = ["FieldType", "FieldTypeBase", "FieldTypeNotFound", "ListFieldRegistry", "registry"]
