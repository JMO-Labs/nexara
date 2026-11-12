"""@file Built-in projecting list field types: date and location."""

from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel

from app.services.list_field_types.base import FieldTypeBase


class DateConfig(BaseModel):
    """@brief Config for DateField."""

    is_due_field: bool = False


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("date must be a YYYY-MM-DD string")
    if len(value) != 10:
        raise ValueError("date must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError("date must be YYYY-MM-DD") from None


class DateField(FieldTypeBase):
    """@brief ISO date; optionally projects to the due_at hot column."""

    key = "date"
    label = "Date"
    config_model = DateConfig

    def validate_value(self, value: Any, config: dict[str, Any]) -> str:
        """@brief Require a YYYY-MM-DD string; return it normalized."""
        if not isinstance(value, str):
            raise ValueError("date must be a YYYY-MM-DD string")
        return _parse_date(value).isoformat()

    def project_columns(self, value: Any, config: dict[str, Any]) -> dict[str, Any]:
        """@brief Project due_at (UTC midnight) only when is_due_field is true."""
        if not config.get("is_due_field") or value is None:
            return {}
        d = _parse_date(value)
        return {"due_at": datetime(d.year, d.month, d.day, tzinfo=UTC)}

    def serialize(self, value: Any) -> Any:
        """@brief date/datetime -> ISO date string."""
        if value is None:
            return None
        return _parse_date(value).isoformat()

    def deserialize(self, raw: Any) -> Any:
        """@brief ISO string -> date."""
        return None if raw is None else _parse_date(raw)


def _coord(value: Any, name: str, limit: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be a number")
    if not -limit <= value <= limit:
        raise ValueError(f"{name} must be between -{limit:g} and {limit:g}")
    return float(value)


class LocationField(FieldTypeBase):
    """@brief {lat, lon} point; projects both to hot columns."""

    key = "location"
    label = "Location"

    def validate_value(self, value: Any, config: dict[str, Any]) -> dict[str, float]:
        """@brief Require dict with in-range float lat/lon."""
        if not isinstance(value, dict) or "lat" not in value or "lon" not in value:
            raise ValueError("location must be an object with lat and lon")
        return {"lat": _coord(value["lat"], "lat", 90), "lon": _coord(value["lon"], "lon", 180)}

    def project_columns(self, value: Any, config: dict[str, Any]) -> dict[str, Any]:
        """@brief Project lat and lon."""
        if not value:
            return {}
        return {"lat": value["lat"], "lon": value["lon"]}
