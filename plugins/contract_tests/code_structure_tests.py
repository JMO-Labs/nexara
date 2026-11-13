"""@file code_structure_tests.py
@brief Directory layout checks: __init__.py, frontend files, unwanted dirs, README/tests.
"""

from __future__ import annotations

from pathlib import Path

from .common import Check, fail, load_manifest_or_none, ok, warn

UNWANTED = (".git", "node_modules", "venv", ".venv")


def run(plugin_dir: Path) -> list[Check]:
    """@brief Run structure checks.
    @param plugin_dir Plugin directory.
    @return Check list.
    """
    out: list[Check] = []
    m = load_manifest_or_none(plugin_dir)
    if m is not None and (m.backend.routes or m.backend.tasks):
        out.append(
            ok("structure.backend_init")
            if (plugin_dir / "__init__.py").is_file()
            else fail("structure.backend_init", "Backend plugins require an __init__.py.")
        )
    if m is not None and m.frontend.slots:
        if not (plugin_dir / "index.tsx").is_file():
            out.append(fail("structure.frontend_index", "frontend.slots set but index.tsx missing."))
        if not (plugin_dir / "components").is_dir():
            out.append(fail("structure.frontend_components", "components/ directory missing."))
    found = sorted({p.name for p in plugin_dir.rglob("*") if p.name in UNWANTED})
    out.append(
        fail("structure.unwanted_files", f"Remove unwanted entries: {', '.join(found)}.")
        if found
        else ok("structure.unwanted_files")
    )
    if any(plugin_dir.rglob("__pycache__")):
        out.append(warn("structure.pycache", "Remove __pycache__ directories before packaging."))
    if not (plugin_dir / "README.md").is_file():
        out.append(warn("structure.readme", "README.md is missing."))
    if not (plugin_dir / "tests").is_dir():
        out.append(warn("structure.tests", "tests/ directory is missing."))
    return out
