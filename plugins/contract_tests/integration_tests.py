"""@file integration_tests.py
@brief Runtime checks: import entries, APIRouter, Celery registration, register_hooks signature.

No database is needed; importing a plugin must not open connections.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from .common import Check, fail, load_manifest_or_none, ok, warn


def _import(plugin_dir: Path, m, rel: str, fresh: bool):  # type: ignore[no-untyped-def]
    from app.plugins.loader import import_entry

    return import_entry(plugin_dir, m, rel, fresh=fresh)


def run(plugin_dir: Path) -> list[Check]:
    """@brief Run integration checks.
    @param plugin_dir Plugin directory.
    @return Check list.
    """
    from fastapi import APIRouter

    m = load_manifest_or_none(plugin_dir)
    if m is None:
        return [fail("integration.manifest", "Manifest invalid; cannot import plugin.")]
    out: list[Check] = []
    if m.backend.routes:
        try:
            mod = _import(plugin_dir, m, m.backend.routes, True)
        except Exception as exc:  # noqa: BLE001
            out.append(fail("integration.import_routes", f"Importing {m.backend.routes}: {exc!r}"))
        else:
            out.append(ok("integration.import_routes"))
            router = getattr(mod, "router", None)
            out.append(
                ok("integration.router")
                if isinstance(router, APIRouter)
                else fail("integration.router", "routes module must expose `router = APIRouter()`.")
            )
            hooks = getattr(mod, "register_hooks", None)
            if hooks is None and (plugin_dir / "hooks.py").is_file():
                hooks = _hooks_from_file(plugin_dir, m)
            out.append(_hooks_check(plugin_dir, hooks))
    if m.backend.tasks:
        out.append(_tasks_check(plugin_dir, m))
    return out


def _hooks_from_file(plugin_dir: Path, m):  # type: ignore[no-untyped-def]
    try:
        return getattr(_import(plugin_dir, m, "hooks.py", False), "register_hooks", None)
    except Exception:  # noqa: BLE001
        return None


def _hooks_check(plugin_dir: Path, fn) -> Check:  # type: ignore[no-untyped-def]
    name = "integration.register_hooks"
    if not (plugin_dir / "hooks.py").is_file() and fn is None:
        return ok(name, "no hooks.py")
    if fn is None:
        return warn(name, "hooks.py present but no register_hooks(community_id, manifest).")
    n = len(inspect.signature(fn).parameters)
    if n != 2:
        return fail(name, f"register_hooks takes {n} parameters; expected (community_id, manifest).")
    return ok(name)


def _defined_in(task, root: Path) -> bool:  # type: ignore[no-untyped-def]
    """@brief True if the task function's source file lives inside ``root``.

    Path-based so tasks preloaded under another module name still count.
    """
    try:
        src = inspect.getsourcefile(inspect.unwrap(task.run))
    except (TypeError, OSError):
        return False
    return src is not None and Path(src).resolve().is_relative_to(root)


def _tasks_check(plugin_dir: Path, m) -> Check:  # type: ignore[no-untyped-def]
    name = "integration.celery_tasks"
    try:
        mod = _import(plugin_dir, m, m.backend.tasks, False)
    except Exception as exc:  # noqa: BLE001
        return fail(name, f"Importing {m.backend.tasks}: {exc!r}")
    from app.tasks.celery_app import celery_app

    root = plugin_dir.resolve()
    mine = [t for t in celery_app.tasks.values() if _defined_in(t, root)]
    if not mine:
        return fail(name, "tasks module registered no Celery tasks (use @celery_app.task).")
    return ok(name, f"{len(mine)} task(s) registered")
