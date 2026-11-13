"""@file _contract.py
@brief Test helper: put ``plugins/`` on sys.path and build throwaway plugins.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PLUGINS = REPO / "plugins"
FIXTURES = REPO / "backend" / "tests" / "fixtures" / "plugins"
sys.dont_write_bytecode = True
if str(PLUGINS) not in sys.path:
    sys.path.insert(0, str(PLUGINS))

BASE = {
    "id": "demo",
    "name": "Demo",
    "version": "1.0.0",
    "author": "me",
    "description": "d",
    "min_core_version": "0.1.0",
    "permissions": [],
}


def make(root: Path, code: str = "", **over) -> Path:
    """@brief Write a plugin dir with manifest overrides and router.py code."""
    d = root / "demo"
    d.mkdir(exist_ok=True)
    data = {**BASE, **over}
    (d / "manifest.json").write_text(json.dumps(data))
    (d / "__init__.py").write_text("")
    (d / "router.py").write_text(code)
    return d


def by_name(checks, name):
    """@brief Checks with the given name."""
    return [c for c in checks if c.name == name]
