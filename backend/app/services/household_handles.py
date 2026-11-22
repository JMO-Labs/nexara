"""
@file household_handles.py
@brief @handles for household members and pets (e.g. ``@biscuit``), so they
       can be mentioned like people. Assigned once at creation and kept
       stable across renames so old mentions keep working.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

MAX_LEN = 30


def slugify(name: str, kind: str) -> str:
    """@brief Lowercase a-z0-9 and dashes, e.g. "Mr. Biscuit" -> "mr-biscuit"."""
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:MAX_LEN].strip("-")
    return s or ("pet" if kind == "pet" else "family")


async def unique_handle(name: str, kind: str, taken: Callable[[str], Awaitable[bool]]) -> str:
    """
    @brief First free handle: base, base-2, base-3, ...
    @param taken async check against household handles, usernames, group slugs
    """
    base = slugify(name, kind)
    for n in range(1, 1000):
        cand = base if n == 1 else f"{base[: MAX_LEN - len(str(n)) - 1]}-{n}"
        if not await taken(cand):
            return cand
    raise RuntimeError("no free handle")  # ponytail: 999 namesakes per community
