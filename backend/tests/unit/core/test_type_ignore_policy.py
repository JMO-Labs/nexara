"""
@file test_type_ignore_policy.py
@brief Guard: type-ignores in app/tasks and app/main.py need a code and reason.
"""

import re
from pathlib import Path

APP = Path(__file__).resolve().parents[3] / "app"
FILES = [*APP.joinpath("tasks").glob("*.py"), APP / "main.py"]
IGNORE = re.compile(r"#\s*type:\s*ignore(?P<code>\[[^\]]+\])?(?P<reason>\s*#\s*\S.*)?")


def test_no_bare_or_unexplained_type_ignore() -> None:
    """@brief Every remaining ignore carries [code] and a trailing reason."""
    bad = []
    for path in FILES:
        for n, line in enumerate(path.read_text().splitlines(), 1):
            m = IGNORE.search(line)
            if m and not (m["code"] and m["reason"]):
                bad.append(f"{path.name}:{n}")
    assert not bad, bad
