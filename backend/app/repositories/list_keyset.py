"""
@file list_keyset.py
@brief Keyset (seek) pagination helpers shared by the list repositories.
"""

from __future__ import annotations

import base64
import json
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any


def encode_cursor(sort_value: Any, row_id: uuid.UUID) -> str:
    """
    @brief Encode a (sort value, id) pair into an opaque cursor.

    @param sort_value Value of the sort column on the last row (datetime or int).
    @param row_id Primary key of the last row (tie-breaker).
    @return URL-safe base64 cursor.
    """
    raw = sort_value.isoformat() if isinstance(sort_value, datetime) else str(sort_value)
    return base64.urlsafe_b64encode(json.dumps([raw, str(row_id)]).encode()).decode()


def decode_cursor(cursor: str | None, cast: Callable[[str], Any]) -> tuple[Any, uuid.UUID] | None:
    """
    @brief Decode a cursor; malformed cursors yield None (first page).

    @param cursor Opaque cursor or None.
    @param cast Converter from the stored string to the sort column type.
    @return (sort value, id) or None.
    """
    if not cursor:
        return None
    try:
        raw, rid = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return cast(raw), uuid.UUID(rid)
    except (ValueError, TypeError):
        return None


def parse_dt(raw: str) -> datetime:
    """@brief Parse an ISO datetime string."""
    return datetime.fromisoformat(raw)
