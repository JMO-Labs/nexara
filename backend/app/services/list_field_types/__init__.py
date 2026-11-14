"""@file Exports the global list field-type registry singleton."""

from app.services.list_field_registry import FieldTypeNotFoundError, ListFieldRegistry
from app.services.list_field_types.base import FieldType, FieldTypeBase
from app.services.list_field_types.base_types import BUILTIN_TYPES
from app.services.list_field_types.builtin import DateField, LocationField
from app.services.list_field_types.special import SignupField, UserPullField

registry = ListFieldRegistry()
for _ft in [*BUILTIN_TYPES, DateField(), LocationField(), SignupField(), UserPullField()]:
    registry.register(_ft)

__all__ = ["FieldType", "FieldTypeBase", "FieldTypeNotFoundError", "ListFieldRegistry", "registry"]
