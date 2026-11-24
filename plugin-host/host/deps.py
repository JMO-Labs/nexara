"""
@file
@brief Dependency install: strict lockfile/requirements validation, then npm/uv
       via a pluggable runner (default: plain subprocess; Task 2 passes a bwrap runner).
"""

import asyncio
import json
import logging
import os
import re
from collections.abc import Awaitable, Callable
from pathlib import Path, PurePosixPath
from typing import Any

from host.errors import InstallError
from host.models import InstallSpec

log = logging.getLogger(__name__)

Runner = Callable[[list[str], Path, int | None], Awaitable[None]]

DEPS_TIMEOUT_S = 600
NPM_REGISTRY = "https://registry.npmjs.org/"
PYPI_INDEX = "https://pypi.org/simple"
PLUGIN_PYTHON = os.environ.get("PLUGIN_HOST_PYTHON", "/usr/local/bin/python3")

_NPM_NAME = r"(@[a-z0-9][a-z0-9._~-]*/)?[a-z0-9][a-z0-9._~-]*"
_LOCK_KEY = re.compile(rf"node_modules/{_NPM_NAME}(/node_modules/{_NPM_NAME})*", re.ASCII)
_SAFE_RANGE = re.compile(r"[0-9A-Za-z.^~<>=|*+ x-]*", re.ASCII)
_DEP_FIELDS = ("dependencies", "optionalDependencies", "peerDependencies", "devDependencies")

_PY_NAME = r"[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?"
_MARKER_VAR = (
    r"(python_version|python_full_version|sys_platform|platform_system|"
    r"platform_machine|os_name|implementation_name)"
)
_CLAUSE = rf'{_MARKER_VAR}\s*(==|!=|<=|>=|<|>)\s*"[A-Za-z0-9._-]*"'
_REQ = re.compile(
    rf"{_PY_NAME}(\[{_PY_NAME}(\s*,\s*{_PY_NAME})*\])?==[0-9][A-Za-z0-9.+!_-]*"
    rf"(\s*;\s*{_CLAUSE}(\s+(and|or)\s+{_CLAUSE})*)?"
    rf"(\s+--hash=sha256:[0-9a-f]{{64}})*",
    re.ASCII,
)


def _unsafe() -> InstallError:
    return InstallError("lockfile_unsafe")


def check_lockfile(root: Path) -> None:
    """
    @brief Require package-lock.json v>=2 whose every package resolves to the npm
    registry over https with an integrity hash (bundled deps excepted); package.json
    may only use plain semver ranges (no git/file/link/url/workspace/alias specs).
    """
    try:
        pj: Any = json.loads((root / "package.json").read_text("utf-8"))
        lock: Any = json.loads((root / "package-lock.json").read_text("utf-8"))
    except (OSError, ValueError) as e:
        raise _unsafe() from e
    if not isinstance(pj, dict) or not isinstance(lock, dict) or "workspaces" in pj:
        raise _unsafe()
    for f in _DEP_FIELDS:
        specs = pj.get(f) or {}
        if not isinstance(specs, dict):
            raise _unsafe()
        for v in specs.values():
            if not isinstance(v, str) or not _SAFE_RANGE.fullmatch(v):
                raise _unsafe()
    ver, pkgs = lock.get("lockfileVersion"), lock.get("packages")
    if not isinstance(ver, int) or ver < 2 or not isinstance(pkgs, dict):
        raise _unsafe()
    for key, entry in pkgs.items():
        if key == "":
            continue
        if not isinstance(entry, dict) or not _LOCK_KEY.fullmatch(key) or entry.get("link"):
            raise _unsafe()
        if ".." in PurePosixPath(key).parts:
            raise _unsafe()
        if entry.get("inBundle") is True and "resolved" not in entry:
            continue
        resolved, integrity = entry.get("resolved"), entry.get("integrity")
        if not (isinstance(resolved, str) and resolved.startswith(NPM_REGISTRY)):
            raise _unsafe()
        if not (isinstance(integrity, str) and integrity.startswith("sha")):
            raise _unsafe()


def check_requirements(root: Path) -> None:
    """
    @brief Only exact pins `name[extras]==ver`, optional simple markers and
    `--hash=sha256:` per line. No options, URLs, paths, includes or env vars.
    """
    try:
        text = (root / "requirements.txt").read_text("utf-8")
    except (OSError, UnicodeError) as e:
        raise InstallError("requirements_unsafe") from e
    for line in re.sub(r"\\\r?\n", " ", text).splitlines():
        line = re.sub(r"(^|\s)#.*$", "", line).strip()
        if line and not _REQ.fullmatch(line):
            raise InstallError("requirements_unsafe")


def install_env(cwd: Path) -> dict[str, str]:
    """
    @brief Minimal env for installers. `cwd` is <data>/plugins/<id>/<version>;
    caches live per plugin in <data>/plugins/<id>/.cache. No host or plugin secrets.
    """
    cache = cwd.parent / ".cache"
    return {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(cache),
        "UV_CACHE_DIR": str(cache / "uv"),
        "UV_NO_CONFIG": "1",
        "UV_PYTHON_DOWNLOADS": "never",
    }


async def run_subprocess(argv: list[str], cwd: Path, uid: int | None) -> None:
    """
    @brief Default runner: unsandboxed subprocess with install_env(). Output is
    discarded, never logged. `uid` is ignored here (the bwrap runner applies it).
    """
    env = install_env(cwd)
    Path(env["HOME"]).mkdir(parents=True, exist_ok=True)
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=cwd,
        env=env,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        rc = await asyncio.wait_for(proc.wait(), DEPS_TIMEOUT_S)
    except (TimeoutError, asyncio.CancelledError):
        proc.kill()
        await proc.wait()
        raise
    if rc != 0:
        log.warning("%s exited with status %s", argv[0], rc)
        raise InstallError(f"deps_failed:exit={rc}")


async def install_deps(
    spec: InstallSpec, root: Path, runner: Runner = run_subprocess, uid: int | None = None
) -> None:
    """@brief Validate then install: node via npm ci, python via uv venv + wheel-only pip."""
    cache = root.parent / ".cache"
    if spec.runtime == "node":
        if (root / "package.json").exists():
            check_lockfile(root)
            # npm refuses one file for both user and global config, hence /nonexistent.
            argv = [
                "npm", "ci", "--omit=dev", "--ignore-scripts",
                "--userconfig=/dev/null", "--globalconfig=/nonexistent/npmrc",
                f"--registry={NPM_REGISTRY}", "--git=/bin/false",
                "--audit=false", "--fund=false", "--update-notifier=false",
                f"--cache={cache / 'npm'}",
            ]  # fmt: skip
            await runner(argv, root, uid)
        return
    has_reqs = (root / "requirements.txt").exists()
    if has_reqs:
        check_requirements(root)
    await runner(["uv", "venv", "--no-config", "--python", PLUGIN_PYTHON, ".venv"], root, uid)
    if has_reqs:
        argv = [
            "uv", "pip", "install", "--no-config", "--no-sources",
            "--only-binary", ":all:", "--index-url", PYPI_INDEX,
            "--python", ".venv/bin/python", "-r", "requirements.txt",
        ]  # fmt: skip
        await runner(argv, root, uid)
