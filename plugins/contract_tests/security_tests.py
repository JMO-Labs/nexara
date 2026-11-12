"""@file security_tests.py
@brief Forbidden imports, hardcoded secrets and HTTP calls without timeout.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from .common import Check, fail, ok, parse, python_files, warn

FORBIDDEN = ("app.api", "app.services", "app.repositories")
ALLOWED = (
    "app.plugins",
    "app.core.dependencies",
    "app.core.exceptions",
    "app.core.config",
    "app.tasks.celery_app",
    "app.db.session",
    "app.models.user",
    "app.models.plugin",
)
SECRET_RES = (
    re.compile(
        r"""(?i)\b(api[_-]?key|secret|password|passwd|token)\w*\s*=\s*["'][^"'\s]{8,}["']"""
    ),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
)
HTTP_VERBS = {"get", "post", "put", "patch", "delete", "head", "request"}
CLIENTS = {"ClientSession", "AsyncClient", "Client"}


def _under(mod: str, prefix: str) -> bool:
    return mod == prefix or mod.startswith(prefix + ".")


def _modules(tree: ast.Module) -> list[tuple[str, int]]:
    mods: list[tuple[str, int]] = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods += [(a.name, n.lineno) for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            if n.module == "app.models":  # ``from app.models import x`` -> app.models.x
                mods += [(f"app.models.{a.name}", n.lineno) for a in n.names]
            else:
                mods.append((n.module, n.lineno))
    return mods


def _http_without_timeout(tree: ast.Module) -> list[int]:
    lines = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call) or any(k.arg == "timeout" for k in n.keywords):
            continue
        f = n.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            if f.value.id in {"requests", "httpx"} and f.attr in HTTP_VERBS | CLIENTS:
                lines.append(n.lineno)
            elif f.value.id == "aiohttp" and f.attr in CLIENTS:
                lines.append(n.lineno)
    return lines


def run(plugin_dir: Path) -> list[Check]:
    """@brief Run security checks.
    @param plugin_dir Plugin directory.
    @return Check list.
    """
    out: list[Check] = []
    bad = False
    for path in python_files(plugin_dir):
        rel = path.relative_to(plugin_dir)
        tree = parse(path)
        if tree is not None:
            for mod, line in _modules(tree):
                if not mod.startswith("app."):
                    continue
                forbidden = any(_under(mod, p) for p in FORBIDDEN) or (
                    mod.startswith("app.models") and not any(_under(mod, a) for a in ALLOWED)
                )
                if forbidden:
                    bad = True
                    out.append(
                        fail(
                            "security.forbidden_import",
                            f"{rel}:{line} imports '{mod}' directly. Plugins must use "
                            "'ctx.db' / plugin_data and the public app.plugins API.",
                        )
                    )
                elif not any(_under(mod, a) for a in ALLOWED):
                    out.append(warn("security.unlisted_import", f"{rel}:{line} imports '{mod}'."))
            for line in _http_without_timeout(tree):
                out.append(warn("security.http_timeout", f"{rel}:{line} HTTP call without timeout."))
        for i, text in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if text.lstrip().startswith("#"):
                continue
            if any(r.search(text) for r in SECRET_RES):
                bad = True
                out.append(fail("security.hardcoded_secret", f"{rel}:{i} looks like a hardcoded secret."))
    if not bad:
        out.insert(0, ok("security.forbidden_patterns"))
    return out
