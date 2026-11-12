"""
@file css.py
@brief Server-side sanitizer for admin-supplied custom CSS.

Regex based deny-list: removes @import, script-bearing url(), expression(),
behavior and vbscript/jscript protocols. Applied to a fixpoint so nested
payloads cannot reassemble after a removal.
"""

from __future__ import annotations

import re

from app.core.exceptions import AppError

MAX_CSS_BYTES = 10240
_MAX_PASSES = 10

_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"@import\s+[^;]+;?", re.I), ""),
    (
        re.compile(r"url\s*\(\s*[\"']?\s*(?:javascript|data|vbscript)\s*:[^)]*\)", re.I),
        'url("")',
    ),
    (re.compile(r"expression\s*\([^)]*\)", re.I), ""),
    (re.compile(r"behavior\s*:\s*[^;}]+;?", re.I), ""),
    (re.compile(r"(?:vb|j)script\s*:", re.I), ""),
    (re.compile(r"</?\s*style", re.I), ""),
]


def sanitize_css(raw_css: str, max_size_bytes: int = MAX_CSS_BYTES) -> str:
    """
    @brief Strip XSS-dangerous constructs from custom CSS.

    @param raw_css Untrusted CSS text.
    @param max_size_bytes Maximum allowed UTF-8 size.
    @return Sanitized CSS.
    @raise AppError css_too_large (400) when over the size limit.
    """
    if len(raw_css.encode("utf-8")) > max_size_bytes:
        raise AppError(
            code="css_too_large",
            message="Custom CSS must be under 10KB",
            status_code=400,
        )
    css = raw_css
    for _ in range(_MAX_PASSES):
        prev = css
        css = _COMMENT.sub("", css)
        for pattern, repl in _PATTERNS:
            css = pattern.sub(repl, css)
        if css == prev:
            break
    return css
