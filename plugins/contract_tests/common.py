"""@file common.py
@brief Shared types and helpers for plugin contract checks.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Status = Literal["pass", "fail", "warn"]
SKIP_DIRS = {"tests", "__pycache__", "node_modules", ".git", "venv", ".venv"}


@dataclass(frozen=True)
class Check:
    """@brief One check outcome."""

    name: str
    status: Status
    message: str = ""


def ok(name: str, message: str = "") -> Check:
    """@brief Passing check."""
    return Check(name, "pass", message)


def fail(name: str, message: str) -> Check:
    """@brief Failing check."""
    return Check(name, "fail", message)


def warn(name: str, message: str) -> Check:
    """@brief Warning check."""
    return Check(name, "warn", message)


def python_files(plugin_dir: Path) -> list[Path]:
    """@brief Plugin ``.py`` files, excluding tests and vendored/cache dirs.
    @param plugin_dir Plugin directory.
    @return Sorted file list.
    """
    out = []
    for p in plugin_dir.rglob("*.py"):
        if SKIP_DIRS.isdisjoint(p.relative_to(plugin_dir).parts[:-1]):
            out.append(p)
    return sorted(out)


def parse(path: Path) -> ast.Module | None:
    """@brief Parse a file, returning None on syntax/decoding errors."""
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError, ValueError):
        return None


def load_manifest_or_none(plugin_dir: Path):  # type: ignore[no-untyped-def]
    """@brief Load the manifest via core ``load_manifest``; None if missing/invalid."""
    from app.plugins.manifest import load_manifest

    try:
        return load_manifest(plugin_dir)
    except Exception:  # noqa: BLE001 - reported by manifest checks
        return None
