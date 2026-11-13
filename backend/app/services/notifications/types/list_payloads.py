"""@file Shared helpers for list notification payloads.

@brief Derives a display title for a list item from its JSONB values.
"""

from typing import Any

TITLE_KEYS = ("title", "name")


def item_title(values: Any) -> str:
    """
    @brief Best-effort title for a list item.

    @param values The item's ``values`` dict.
    @return ``title``/``name`` value, else the first non-empty string, else "".
    """
    if not isinstance(values, dict):
        return ""
    for key in TITLE_KEYS:
        if isinstance(values.get(key), str) and values[key]:
            return str(values[key])
    for value in values.values():
        if isinstance(value, str) and value:
            return value
    return ""
