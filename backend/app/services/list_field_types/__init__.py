"""@file Exports the global list field-type registry singleton."""

from app.services.list_field_registry import FieldTypeNotFound, ListFieldRegistry
from app.services.list_field_types.base import FieldType, FieldTypeBase

registry = ListFieldRegistry()

__all__ = ["FieldType", "FieldTypeBase", "FieldTypeNotFound", "ListFieldRegistry", "registry"]
