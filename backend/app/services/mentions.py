"""
@file mentions.py
@brief Pure @username mention extraction (no DB or service dependencies).
"""

from __future__ import annotations

import re

_FENCE = re.compile(r"(`+)")
_MENTION = re.compile(r"@([a-zA-Z0-9_-]+)")


def extract(content: str) -> list[str]:
    """
    @brief Extract unique @username mentions, skipping backtick code spans/fences.
    @param content Plain text or markdown content.
    @return Usernames (without @) in first-seen order, deduplicated.
    """
    result: list[str] = []
    open_run: str | None = None
    for part in _FENCE.split(content):
        if not part:
            continue
        if part.startswith("`"):
            if open_run is None:
                open_run = part
            elif part == open_run:
                open_run = None
            continue
        if open_run is None:
            result.extend(m.group(1) for m in _MENTION.finditer(part))
    return list(dict.fromkeys(result))
