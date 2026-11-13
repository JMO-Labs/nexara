"""@file permission_tests.py
@brief Static (ast) comparison of declared permissions against actual usage.
"""

from __future__ import annotations

import ast
from pathlib import Path

from .common import Check, fail, load_manifest_or_none, ok, parse, python_files, warn

HTTP_MODULES = {"requests", "aiohttp", "httpx", "urllib.request"}


def _is_ctx(node: ast.expr) -> bool:
    return (isinstance(node, ast.Name) and node.id == "ctx") or (
        isinstance(node, ast.Attribute) and node.attr == "ctx"
    )


def detect_usage(plugin_dir: Path) -> set[str]:
    """@brief Permission names whose capability the plugin code uses.
    @param plugin_dir Plugin directory.
    @return Subset of {db, send_notifications, external_http, storage_access, celery_tasks}.
    """
    used: set[str] = set()
    for path in python_files(plugin_dir):
        tree = parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and _is_ctx(node.value):
                used |= {
                    "db": {"db"},
                    "notify": {"send_notifications"},
                    "storage": {"storage_access"},
                    "http_client": {"external_http"},
                }.get(node.attr, set())
            elif isinstance(node, ast.Import):
                if any(a.name in HTTP_MODULES for a in node.names):
                    used.add("external_http")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module in HTTP_MODULES or node.module.split(".")[0] in HTTP_MODULES:
                    used.add("external_http")
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for dec in node.decorator_list:
                    target = dec.func if isinstance(dec, ast.Call) else dec
                    if isinstance(target, ast.Attribute) and target.attr == "task":
                        used.add("celery_tasks")
                    elif isinstance(target, ast.Name) and target.id == "shared_task":
                        used.add("celery_tasks")
    return used


def run(plugin_dir: Path) -> list[Check]:
    """@brief Run permission usage checks.
    @param plugin_dir Plugin directory.
    @return Check list.
    """
    m = load_manifest_or_none(plugin_dir)
    if m is None:
        return [fail("permissions.manifest", "Manifest invalid; cannot check permissions.")]
    declared = {p.value for p in m.permissions}
    used = detect_usage(plugin_dir)
    out: list[Check] = []
    groups = {
        "db": ({"db_read", "db_write"}, "ctx.db"),
        "send_notifications": ({"send_notifications"}, "ctx.notify"),
        "external_http": ({"external_http"}, "an HTTP client (requests/aiohttp/httpx)"),
        "storage_access": ({"storage_access"}, "ctx.storage"),
        "celery_tasks": ({"celery_tasks"}, "@celery_app.task"),
    }
    for key, (perms, what) in groups.items():
        name = f"permissions.{key}"
        has = bool(perms & declared)
        label = "/".join(sorted(perms))
        if key in used and not has:
            out.append(fail(name, f"Code uses {what} but '{label}' is not declared in manifest."))
        elif has and key not in used:
            out.append(warn(name, f"Permission '{label}' declared but unused. Safe to remove."))
        else:
            out.append(ok(name))
    return out
