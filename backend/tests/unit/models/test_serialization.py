"""
@file test_serialization.py
@brief Unit tests for the export model serializer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.models import serialization
from app.models.serialization import _json_value, serialize


def test_json_value_converts_types() -> None:
    uid = uuid.uuid4()
    assert _json_value(Decimal("1.5")) == 1.5
    assert _json_value(uid) == str(uid)
    assert _json_value(date(2026, 1, 2)) == "2026-01-02"
    assert _json_value(datetime(2026, 1, 2, tzinfo=UTC)).startswith("2026-01-02T")
    assert _json_value("x") == "x"


def test_serialize_omits_sensitive_columns() -> None:
    from app.models.user import User

    user = User(id=uuid.uuid4(), email="a@b.c", password_hash="h")
    out = serialize(user)
    assert out["email"] == "a@b.c"
    assert not any(m in k for k in out for m in serialization.SENSITIVE_MARKERS)
