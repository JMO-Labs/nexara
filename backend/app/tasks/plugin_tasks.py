"""
@file plugin_tasks.py
@brief Registers Celery tasks shipped by bundled plugins (loaded by file path).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PLUGINS = Path(__file__).resolve().parents[3] / "plugins"


def _load(plugin_id: str, module: str) -> None:
    path = _PLUGINS / plugin_id / f"{module}.py"
    name = f"nexara_plugin_{plugin_id.replace('-', '_')}_{module}"
    if name in sys.modules or not path.is_file():
        return
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)


_load("example-trivia", "tasks")
