"""@file reporting.py
@brief Format check results as JSON or human-readable text.
"""

from __future__ import annotations

from .common import Check

DOCS = "https://docs.nexara.app/plugins/contract#"
MARKS = {"pass": "✓", "fail": "✗", "warn": "!"}
COLORS = {"pass": "\033[32m", "fail": "\033[31m", "warn": "\033[33m"}
KEY = {"pass": "passed", "fail": "failed", "warn": "warnings"}


def to_dict(checks: list[Check]) -> dict[str, object]:
    """@brief Build the JSON report. @return {passed, failed, warnings, checks}."""
    counts = {v: sum(1 for c in checks if k == c.status) for k, v in KEY.items()}
    return {
        **counts,
        "checks": [{"name": c.name, "status": c.status, "message": c.message} for c in checks],
    }


def to_text(checks: list[Check], color: bool = False) -> str:
    """@brief Human-readable report (check / X / ! markers, docs link per non-pass).
    @param checks Results.
    @param color Emit ANSI colors.
    @return Multi-line string.
    """
    lines = []
    for c in checks:
        mark = MARKS[c.status]
        if color:
            mark = f"{COLORS[c.status]}{mark}\033[0m"
        line = f"{mark} {c.name}" + (f": {c.message}" if c.message else "")
        if c.status != "pass":
            line += f"\n    see {DOCS}{c.name.replace('.', '-')}"
        lines.append(line)
    d = to_dict(checks)
    lines.append(f"\n{d['passed']} passed, {d['failed']} failed, {d['warnings']} warnings")
    return "\n".join(lines)
