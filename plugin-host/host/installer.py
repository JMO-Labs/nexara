"""
@file
@brief Package installer: https download, sha256 check, safe tar extraction,
       dependency install (no scripts, wheels only) and atomic `current` swap.
"""

import asyncio
import hashlib
import hmac
import io
import logging
import os
import shutil
import tarfile
import tomllib
import uuid
from pathlib import Path, PurePosixPath

import httpx

from host.models import InstallSpec

log = logging.getLogger(__name__)

MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
MAX_EXTRACT_BYTES = 200 * 1024 * 1024
MAX_MEMBERS = 10_000
DEPS_TIMEOUT_S = 600
SHA_MARKER = ".nexara-sha256"
MANIFEST = "nexara-plugin.toml"


class InstallError(Exception):
    """@brief Install failure; `code` is reported as last_error (no secrets)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


async def _https_only(request: httpx.Request) -> None:
    if request.url.scheme != "https":
        raise InstallError("download_failed")


async def _download(url: str) -> bytes:
    """
    @brief GET `url` over https only (redirects included), capped at MAX_DOWNLOAD_BYTES.
    @return Package bytes.
    """
    if not url.startswith("https://"):
        raise InstallError("download_failed")
    buf = bytearray()
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            max_redirects=5,
            timeout=60,
            event_hooks={"request": [_https_only]},
        ) as client:
            async with client.stream("GET", url) as r:
                if r.status_code != 200:
                    raise InstallError("download_failed")
                if int(r.headers.get("content-length") or 0) > MAX_DOWNLOAD_BYTES:
                    raise InstallError("package_too_large")
                async for chunk in r.aiter_bytes():
                    buf += chunk
                    if len(buf) > MAX_DOWNLOAD_BYTES:
                        raise InstallError("package_too_large")
    except httpx.HTTPError as e:
        raise InstallError("download_failed") from e
    return bytes(buf)


def _safe_extract(data: bytes, dest: Path) -> None:
    """
    @brief Extract a .tar(.gz) into `dest`, allowing only regular files and dirs.
    Rejects absolute paths, `..`, links, devices/fifos, too many members and size bombs.
    """
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
            total = 0
            members = []
            for m in tf:
                parts = PurePosixPath(m.name).parts
                if m.name.startswith(("/", "\\")) or ".." in parts or "\0" in m.name:
                    raise InstallError("unsafe_archive")
                if not (m.isfile() or m.isdir()):
                    raise InstallError("unsafe_archive")
                total += m.size
                members.append(m)
                if total > MAX_EXTRACT_BYTES or len(members) > MAX_MEMBERS:
                    raise InstallError("unsafe_archive")
            tf.extractall(dest, members=members, filter="data")
    except (tarfile.TarError, OSError, EOFError) as e:
        raise InstallError("invalid_archive") from e


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


async def _run(argv: list[str], cwd: Path) -> None:
    """
    @brief Run an installer subprocess with a minimal env (no plugin secrets).
    `cwd` is <data>/plugins/<id>/<version>; caches live in <data>/.cache.
    """
    home = cwd.parents[2] / ".cache"
    home.mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(home),
        "UV_CACHE_DIR": str(home / "uv"),
        "UV_NO_CONFIG": "1",
        "UV_PYTHON_DOWNLOADS": "never",
        "npm_config_cache": str(home / "npm"),
        "npm_config_update_notifier": "false",
    }
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=cwd,
        env=env,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), DEPS_TIMEOUT_S)
    except (TimeoutError, asyncio.CancelledError):
        proc.kill()
        await proc.wait()
        raise
    if proc.returncode != 0:
        log.warning(
            "%s failed (%s): %s", argv[0], proc.returncode, out[-2000:].decode(errors="replace")
        )
        raise InstallError("deps_failed")


async def _install_deps(spec: InstallSpec, root: Path) -> None:
    """@brief node: npm ci without scripts; python: venv + wheel-only pip install."""
    if spec.runtime == "node":
        if (root / "package.json").is_file():
            await _run(["npm", "ci", "--omit=dev", "--ignore-scripts"], root)
        return
    await _run(["uv", "venv", ".venv"], root)
    if (root / "requirements.txt").is_file():
        await _run(
            [
                "uv",
                "pip",
                "install",
                "--only-binary",
                ":all:",
                "--python",
                ".venv/bin/python",
                "-r",
                "requirements.txt",
            ],
            root,
        )


def _swap_current(pdir: Path, version: str) -> None:
    """@brief Atomically point <pdir>/current at `version`, then prune other versions."""
    tmp = pdir / f".current-{uuid.uuid4().hex}"
    tmp.symlink_to(version)
    os.replace(tmp, pdir / "current")
    for d in pdir.iterdir():
        if d.name in (version, "current"):
            continue
        if d.is_symlink() or d.is_file():
            d.unlink()
        else:
            shutil.rmtree(d, ignore_errors=True)


async def install(plugin_id: str, spec: InstallSpec, data_dir: Path) -> Path:
    """
    @brief Download, verify, extract and prepare a plugin version, then swap `current`.
    @param plugin_id Validated plugin id (path-safe).
    @param spec Install request; `spec.env` is not touched here.
    @param data_dir Host data root (/data).
    @return Path of the installed version dir. Previous version stays until success.
    """
    pdir = data_dir / "plugins" / plugin_id
    pdir.mkdir(parents=True, exist_ok=True)
    root = pdir / spec.version
    current = pdir / "current"
    sha = spec.sha256.lower()
    if root.exists():
        if current.exists() and current.resolve() == root.resolve():
            marker = root / SHA_MARKER
            if marker.is_file() and hmac.compare_digest(marker.read_text().strip(), sha):
                return root
            raise InstallError("version_conflict")
        shutil.rmtree(root)

    data = await _download(spec.package_url)
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), sha):
        raise InstallError("sha256_mismatch")
    try:
        root.mkdir()
        await asyncio.to_thread(_safe_extract, data, root)
        _check_manifest(plugin_id, spec, root)
        await _install_deps(spec, root)
        (root / SHA_MARKER).write_text(sha)
    except BaseException:
        shutil.rmtree(root, ignore_errors=True)
        raise
    _swap_current(pdir, spec.version)
    return root
