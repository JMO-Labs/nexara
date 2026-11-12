"""@file Tests for built-in projecting list field types (date, location)."""

from datetime import UTC, date, datetime

import pytest

from app.services.list_field_types import registry
from app.services.list_field_types.builtin import DateField, LocationField


def test_registered():
    assert {"date", "location"} <= set(registry.keys())
    assert isinstance(registry.get("date"), DateField)
    assert isinstance(registry.get("location"), LocationField)


class TestDateField:
    ft = DateField()

    def test_validate_ok(self):
        assert self.ft.validate_value("2026-03-04", {}) == "2026-03-04"

    @pytest.mark.parametrize("bad", ["03/04/2026", "2026-13-01", "", 5, None])
    def test_validate_bad(self, bad):
        with pytest.raises(ValueError):
            self.ft.validate_value(bad, {})

    def test_config_default(self):
        assert self.ft.validate_config({}) == {"is_due_field": False}

    def test_projects_due_at_when_flag(self):
        cols = self.ft.project_columns("2026-03-04", {"is_due_field": True})
        assert cols == {"due_at": datetime(2026, 3, 4, tzinfo=UTC)}

    def test_no_projection_without_flag(self):
        assert self.ft.project_columns("2026-03-04", {"is_due_field": False}) == {}
        assert self.ft.project_columns("2026-03-04", {}) == {}

    def test_serialize_deserialize(self):
        assert self.ft.serialize(date(2026, 3, 4)) == "2026-03-04"
        assert self.ft.serialize(datetime(2026, 3, 4, 9, 0, tzinfo=UTC)) == "2026-03-04"
        assert self.ft.serialize("2026-03-04") == "2026-03-04"
        assert self.ft.deserialize("2026-03-04") == date(2026, 3, 4)
        assert self.ft.deserialize(None) is None


class TestLocationField:
    ft = LocationField()

    def test_validate_ok(self):
        v = {"lat": 48.5, "lon": -120}
        assert self.ft.validate_value(v, {}) == {"lat": 48.5, "lon": -120.0}

    @pytest.mark.parametrize(
        "bad",
        [
            {"lat": 91, "lon": 0},
            {"lat": -91, "lon": 0},
            {"lat": 0, "lon": 181},
            {"lat": 0, "lon": -181},
            {"lat": "1", "lon": 0},
            {"lat": True, "lon": 0},
            {"lat": 0},
            "1,2",
            None,
        ],
    )
    def test_validate_bad(self, bad):
        with pytest.raises(ValueError):
            self.ft.validate_value(bad, {})

    def test_projects_both(self):
        assert self.ft.project_columns({"lat": 1.5, "lon": 2.5}, {}) == {"lat": 1.5, "lon": 2.5}

    def test_serialize_passthrough(self):
        v = {"lat": 1.0, "lon": 2.0}
        assert self.ft.serialize(v) == v
        assert self.ft.deserialize(v) == v
