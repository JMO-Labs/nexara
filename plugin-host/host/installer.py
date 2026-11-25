"""
@file
@brief Install orchestration: download → sha256 → safe extract → manifest check →
       deps → sha marker. `current` is swapped (and old versions pruned) by the caller
       only after the new process started.
"""

import asyncio
import hashlib
import hmac
import logging
import os
import shutil
import tomllib
import uuid
from pathlib import Path

from host.archive import safe_extract
from host.cleanup import remove_tree
from host.deps import Runner, install_deps, run_subprocess
from host.download import fetch
from host.errors import InstallError
from host.models import InstallSpec

log = logging.getLogger(__name__)

__all__ = ["InstallError", "install", "prune", "swap_current"]

SHA_MARKER = ".nexara-sha256"
MANIFEST = "nexara-plugin.toml"
CACHE_DIR = ".cache"


def _check_manifest(plugin_id: str, spec: InstallSpec, root: Path) -> None:
    """@brief Manifest id/version must match the request; entrypoint must exist."""
    try:
        meta = tomllib.loads((root / MANIFEST).read_text("utf-8"))["plugin"]
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, KeyError, TypeError) as e:
        raise InstallError("manifest_invalid") from e
    if meta.get("id") != plugin_id or meta.get("version") != spec.version:
        raise InstallError("manifest_mismatch")
    ep = root / spec.entrypoint
    if ep.is_symlink() or not ep.is_file():
        raise InstallError("entrypoint_missing")


def current_version(pdir: Path) -> str | None:
    """@brief Name of the version dir `current` points at, if any."""
    cur = pdir / "current"
    return cur.resolve().name if cur.is_symlink() and cur.exists() else None


def swap_current(pdir: Path, version: str) -> None:
    """@brief Atomically point <pdir>/current at `version`."""
    tmp = pdir / f".current-{uuid.uuid4().hex}"
    tmp.symlink_to(version)
    os.replace(tmp, pdir / "current")


def _log_rm(func: object, path: str, exc: BaseException) -> None:
    log.error("prune: cannot remove %s: %s", path, type(exc).__name__)


def prune(pdir: Path, keep: str) -> None:
    """@brief Remove every version dir except `keep` (and `current`, the cache)."""
    for d in pdir.iterdir():
        if d.name in (keep, "current", CACHE_DIR):
            continue
        if d.is_symlink() or d.is_file():
            d.unlink()
        else:
            shutil.rmtree(d, onexc=_log_rm)


async def install(
    plugin_id: str,
    spec: InstallSpec,
    data_dir: Path,
    *,
    runner: Runner = run_subprocess,
    uid: int | None = None,
) -> Path:
    """
    @brief Download, verify, extract and prepare a plugin version (no swap).
    @param plugin_id Validated plugin id (path-safe).
    @param spec Install request; `spec.env` is not touched here.
    @param data_dir Host data root (/data).
    @param runner Executes npm/uv (argv, cwd, uid).
    @param uid Plugin uid the runner should install as.
    @return The version dir. Re-PUT of the current version with the same sha is a no-op.
    """
    pdir = data_dir / "plugins" / plugin_id
    root = pdir / spec.version
    if any(p.is_symlink() for p in (pdir.parent, pdir, root)):
        raise InstallError("unsafe_path")  # before any mkdir/rmtree/write through it
    pdir.mkdir(parents=True, exist_ok=True)
    sha = spec.sha256.lower()
    if root.exists():
        if current_version(pdir) == spec.version:
            marker = root / SHA_MARKER
            if marker.is_file() and hmac.compare_digest(marker.read_text().strip(), sha):
                return root
            raise InstallError("version_conflict")
        if not await remove_tree(root, uid, data_dir):
            raise InstallError("cleanup_failed")

    data = await fetch(spec.package_url)
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), sha):
        raise InstallError("sha256_mismatch")
    try:
        root.mkdir()
        await asyncio.to_thread(safe_extract, data, root)
        del data
        _check_manifest(plugin_id, spec, root)
        await install_deps(spec, root, runner, uid)
        (root / SHA_MARKER).write_text(sha)
    except BaseException:
        await remove_tree(root, uid, data_dir)  # logs anything it cannot remove
        raise
    return root
