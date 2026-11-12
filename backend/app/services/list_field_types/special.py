"""@file Special list field types: signup and user_pull."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.services.list_field_types.base import FieldTypeBase


class SignupConfig(BaseModel):
    """@brief Config for signup slots."""

    default_quantity_needed: int = Field(default=1, ge=1)


class SignupField(FieldTypeBase):
    """@brief Marks an item as a signup slot with a needed quantity."""

    key = "signup"
    label = "Signup"
    config_model = SignupConfig

    def validate_value(self, value: Any, config: dict[str, Any]) -> Any:
        """@brief Require an int >= 1 (bool rejected)."""
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("signup value must be an integer >= 1")
        return value

    def project_columns(self, value: Any, config: dict[str, Any]) -> dict[str, Any]:
        """@return signup_quantity_needed from config default."""
        qty = config.get("default_quantity_needed", 1)
        return {"signup_quantity_needed": qty}


class UserPullConfig(BaseModel):
    """@brief Config for user-data pull fields."""

    pull_from: Literal["email", "phone", "address", "birthday"]
    target_user_field: Optional[str] = None


class UserPullField(FieldTypeBase):
    """@brief Resolved live at read time; never stored."""

    key = "user_pull"
    label = "User pull"
    config_model = UserPullConfig

    def serialize(self, value: Any) -> Any:
        """@return None; value is not persisted."""
        return None

    def deserialize(self, raw: Any) -> Any:
        """@return None; resolved at read time."""
        return None
