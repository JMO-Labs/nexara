"""
@file serialization.py
@brief Generic model-to-dict serializer for data exports.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect

SENSITIVE_MARKERS = ("password", "secret", "token", "hash")
SKIPPED_COLUMNS = frozenset({"search_fts"})


def _is_excluded(name: str) -> bool:
    return name in SKIPPED_COLUMNS or any(m in name for m in SENSITIVE_MARKERS)


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    return value


def serialize(obj: Any) -> dict[str, Any]:
    """
    @brief Convert a mapped instance to a JSON-safe dict, omitting secrets.
    @param obj SQLAlchemy model instance.
    @return Column-name keyed dict without password/secret/token/hash columns.
    """
    return {
        attr.key: _json_value(getattr(obj, attr.key))
        for attr in inspect(type(obj)).column_attrs
        if not _is_excluded(attr.key)
    }
