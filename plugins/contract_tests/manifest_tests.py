"""@file manifest_tests.py
@brief Manifest checks: core schema (reused) plus paths, duplicate hooks, deprecated fields.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .common import Check, fail, ok, warn

REQUIRED = ("id", "name", "version", "author", "description", "min_core_version")
DEPRECATED = {"entry": "use [backend] routes", "router": "use [backend] routes"}


def _raw(plugin_dir: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """@brief Read the raw manifest. @return (data, duplicate key names)."""
    dupes: list[str] = []

    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        keys = [k for k, _ in pairs]
        dupes.extend(sorted({k for k in keys if keys.count(k) > 1}))
        return dict(pairs)

    toml_p, json_p = plugin_dir / "manifest.toml", plugin_dir / "manifest.json"
    try:
        if toml_p.is_file():
            return tomllib.loads(toml_p.read_text(encoding="utf-8")), dupes
        if json_p.is_file():
            return json.loads(json_p.read_text(encoding="utf-8"), object_pairs_hook=hook), dupes
    except (ValueError, OSError):
        return None, dupes
    return None, dupes


def _path_checks(plugin_dir: Path, data: dict[str, Any]) -> list[Check]:
    root = plugin_dir.resolve()
    out: list[Check] = []
    backend = data.get("backend") if isinstance(data.get("backend"), dict) else {}
    for key in ("routes", "tasks"):
        rel = backend.get(key)
        if not rel:
            continue
        p = (root / str(rel)).resolve()
        name = f"manifest.backend_{key}_path"
        if not p.is_relative_to(root):
            out.append(fail(name, f"backend.{key} '{rel}' escapes the plugin directory."))
        elif not p.is_file():
            out.append(fail(name, f"backend.{key} '{rel}' does not exist in the plugin."))
        else:
            out.append(ok(name))
    return out


def run(plugin_dir: Path) -> list[Check]:
    """@brief Run manifest checks.
    @param plugin_dir Plugin directory.
    @return Check list.
    """
    from app.plugins.manifest import load_manifest

    data, dupes = _raw(plugin_dir)
    if data is None:
        return [fail("manifest.found", "manifest.toml/manifest.json missing or unparseable.")]
    out = [ok("manifest.found")]
    missing = [f for f in REQUIRED if f not in data]
    out.append(
        fail("manifest.required_fields", f"Missing required fields: {', '.join(missing)}.")
        if missing
        else ok("manifest.required_fields")
    )
    out.append(
        fail("manifest.duplicate_keys", f"Duplicate keys (e.g. hooks): {', '.join(dupes)}.")
        if dupes
        else ok("manifest.duplicate_keys")
    )
    deprecated = [k for k in DEPRECATED if k in data]
    for k in deprecated:
        out.append(warn("manifest.deprecated_field", f"'{k}' is deprecated: {DEPRECATED[k]}."))
    hooks = data.get("hooks") if isinstance(data.get("hooks"), dict) else {}
    norm = [h.removeprefix("on_") for h in hooks]
    clash = sorted({h for h in norm if norm.count(h) > 1})
    if clash:
        out.append(fail("manifest.duplicate_hooks", f"Duplicate hook names: {', '.join(clash)}."))
    try:
        m = load_manifest(plugin_dir)
    except ValidationError as exc:
        reported = False
        for err in exc.errors():
            loc = str(err["loc"][0]) if err["loc"] else "schema"
            if err["type"] == "missing" or (err["type"] == "extra_forbidden" and loc in DEPRECATED):
                continue
            reported = True
            out.append(fail(f"manifest.{loc}", f"{loc}: {err['msg']}"))
        if not reported and not (missing or dupes or deprecated):
            out.append(fail("manifest.schema", "Manifest failed core validation."))
    else:
        out.append(ok("manifest.schema"))
        if m.id.endswith(("-", "_")):
            out.append(warn("manifest.id_suffix", f"id '{m.id}' should not end with '-' or '_'."))
    out.extend(_path_checks(plugin_dir, data))
    return out
