"""@file Field type protocol and default base class for list fields."""

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class FieldType(Protocol):
    """@brief Contract every list field type implements."""

    key: str
    label: str
    config_model: type[BaseModel]

    def validate_config(self, config: dict[str, Any]) -> dict[str, Any]: ...
    def validate_value(self, value: Any, config: dict[str, Any]) -> Any: ...
    def project_columns(self, value: Any, config: dict[str, Any]) -> dict[str, Any]: ...
    def serialize(self, value: Any) -> Any: ...
    def deserialize(self, raw: Any) -> Any: ...


class FieldTypeBase:
    """@brief Default implementations; subclasses set key/label and override validate_value."""

    key: str = ""
    label: str = ""
    config_model: type[BaseModel] = BaseModel

    def validate_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """@brief Validate config through config_model; return normalized dict."""
        return self.config_model(**config).model_dump()

    def validate_value(self, value: Any, config: dict[str, Any]) -> Any:
        """@brief Return value as-is by default."""
        return value

    def project_columns(self, value: Any, config: dict[str, Any]) -> dict[str, Any]:
        """@brief Typed column projection; none by default."""
        return {}

    def serialize(self, value: Any) -> Any:
        """@brief Convert value to storable form."""
        return value

    def deserialize(self, raw: Any) -> Any:
        """@brief Convert stored form to value."""
        return raw
