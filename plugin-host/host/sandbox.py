"""
@file
@brief bubblewrap sandbox: argv builders for plugin processes and dependency installs,
       per-plugin uid allocation, plugin env and the startup self-test.

Every plugin sees a read-only host root with `/data` masked by a tmpfs, its own code
read-only at /plugin and its state read-write at /state. The image must provide the
empty mountpoints /plugin and /state (the root is mounted read-only, so bwrap cannot
create them).
"""

import asyncio
import json
import logging
import os
import stat
import subprocess
from pathlib import Path
from typing import TypedDict

from host.deps import DEPS_TIMEOUT_S, Runner, install_env
from host.errors import InstallError
from host.models import PluginEnv

log = logging.getLogger(__name__)

BWRAP = "bwrap"
UID_BASE = 20000
PROBE_UID = UID_BASE - 1  # self-test runs as this unprivileged uid
MOUNTPOINTS = (Path("/plugin"), Path("/state"))
PLUGIN_PATH = "/usr/local/bin:/usr/bin:/bin"
_NS_FLAGS = ["--unshare-pid", "--unshare-ipc", "--die-with-parent", "--new-session"]


def _within(path: Path, parent: Path) -> Path:
    """@brief Resolve `path` (following symlinks) and require it to be directly in `parent`."""
    real = path.resolve()
    if real.parent != parent.resolve():
        raise ValueError("path outside the plugin's own directory")
    return real


def _common(data_dir: Path) -> list[str]:
    """@brief Read-only root, private /tmp, host data masked."""
    return [
        BWRAP,
        "--ro-bind", "/", "/",
        "--tmpfs", "/tmp",
        "--tmpfs", str(data_dir),
    ]  # fmt: skip


def _tail(uid: int) -> list[str]:
    """@brief Fresh /proc and /dev, private namespaces, uid/gid inside, no capabilities."""
    return [
        "--proc", "/proc",
        "--dev", "/dev",
        *_NS_FLAGS,
        "--unshare-user", "--uid", str(uid), "--gid", str(uid),
        "--cap-drop", "ALL",
    ]  # fmt: skip


def bwrap_argv(
    plugin_id: str,
    uid: int,
    root: Path,
    state: Path,
    runtime: str,
    entrypoint: str,
    *,
    data_dir: Path = Path("/data"),
) -> list[str]:
    """
    @brief Full argv to run a plugin under bwrap.
    @param root Version dir; must resolve to <data>/plugins/<plugin_id>/<version>.
    @param state Must resolve to <data>/plugin-state/<plugin_id>.
    @raise ValueError if either dir belongs to another plugin.
    """
    root = _within(root, data_dir / "plugins" / plugin_id)
    if _within(state, data_dir / "plugin-state").name != plugin_id:
        raise ValueError("state dir of another plugin")
    state = state.resolve()
    cmd = ["node", entrypoint]
    if runtime == "python":  # venv shebangs point at the install path, so call python directly
        cmd = ["/plugin/.venv/bin/python", "-u", entrypoint]
    return [
        *_common(data_dir),
        "--ro-bind", str(root), "/plugin",
        "--bind", str(state), "/state",
        *_tail(uid),
        "--chdir", "/plugin",
        "--", *cmd,
    ]  # fmt: skip


def install_argv(argv: list[str], cwd: Path, uid: int, data_dir: Path) -> list[str]:
    """
    @brief Wrap an install step: only the version dir and the plugin's cache are visible
    (at their real paths, which npm/uv args and install_env() refer to). Network allowed.
    """
    pdir = cwd.resolve().parent
    if pdir.parent != (data_dir / "plugins").resolve():
        raise ValueError("install dir outside <data>/plugins/<id>/")
    cwd, cache = cwd.resolve(), pdir / ".cache"
    return [
        *_common(data_dir),
        "--bind", str(cwd), str(cwd),
        "--bind", str(cache), str(cache),
        *_tail(uid),
        "--chdir", str(cwd),
        "--", *argv,
    ]  # fmt: skip


def plugin_env(env: PluginEnv, port: int) -> dict[str, str]:
    """@brief The plugin's entire process env: NEXARA_* + PORT + minimal PATH/HOME."""
    out = {k: v for k, v in env.model_dump().items() if v is not None}
    url = out.get("NEXARA_URL") or os.environ.get("NEXARA_URL")
    out.pop("NEXARA_URL", None)
    if url:
        out = {"NEXARA_URL": url, **out}
    out.update(NEXARA_DATA_DIR="/state", PORT=str(port), PATH=PLUGIN_PATH, HOME="/tmp")
    return out


def plugin_uid(data_dir: Path, plugin_id: str) -> int:
    """@brief UID_BASE + stable index from <data>/uids.json (allocated on first use, kept)."""
    path = data_dir / "uids.json"
    uids: dict[str, int] = json.loads(path.read_text()) if path.exists() else {}
    if plugin_id not in uids:
        uids[plugin_id] = max(uids.values(), default=-1) + 1
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(uids))
        os.replace(tmp, path)
    return UID_BASE + uids[plugin_id]


def is_root() -> bool:
    return os.geteuid() == 0


def _walk(path: Path) -> list[str]:
    """@brief `path` and everything below it (symlinks not followed)."""
    out = [str(path)]
    for dirpath, dirnames, filenames in os.walk(path):
        out += [os.path.join(dirpath, n) for n in dirnames + filenames]
    return out


def chown_tree(path: Path, uid: int) -> None:
    """@brief chown -R uid:uid (install time: the plugin may write it). Root only."""
    if not is_root() or not path.exists():
        return
    for p in _walk(path):
        os.chown(p, uid, uid, follow_symlinks=False)


def sealed_mode(mode: int) -> int:
    """@brief Owner bits kept (no setuid/setgid/sticky); group r + x-if-owner-x; other none."""
    owner = stat.S_IMODE(mode) & 0o700
    return owner | 0o040 | (0o010 if owner & 0o100 else 0)


def seal_tree(path: Path, uid: int) -> None:
    """
    @brief After install: root:uid, group read(+exec where owner has it), no group/other
    write. The plugin can read its code and cache but never modify them. Root only.
    """
    if not is_root() or not path.exists():
        return
    for p in _walk(path):
        st = os.lstat(p)
        os.chown(p, 0, uid, follow_symlinks=False)
        if stat.S_ISLNK(st.st_mode):
            continue
        os.chmod(p, sealed_mode(st.st_mode))


def prepare_state(state: Path, uid: int) -> None:
    """@brief Create the plugin's state dir, owned by its uid, mode 0700."""
    state.mkdir(parents=True, exist_ok=True)
    if is_root():
        os.chown(state, uid, uid, follow_symlinks=False)
    state.chmod(0o700)


class Creds(TypedDict):
    """@brief Popen kwargs that drop to a plugin uid (empty supplementary groups)."""

    user: int | None
    group: int | None
    extra_groups: list[int] | None


def as_user(uid: int | None) -> Creds:
    """@brief Popen kwargs to drop to `uid` (only possible, and required, as root)."""
    if uid is None or not is_root():
        return Creds(user=None, group=None, extra_groups=None)
    return Creds(user=uid, group=uid, extra_groups=[])


def _bwrap_ok(args: list[str]) -> bool:
    try:
        proc = subprocess.run(
            [BWRAP, *args],
            env={"PATH": PLUGIN_PATH},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=10,
            **as_user(PROBE_UID),
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def self_test() -> bool:
    """
    @brief `bwrap --ro-bind / / true`, then the namespaces/mounts plugins actually use
    (a fresh /proc needs e.g. docker `systempaths=unconfined`), both as an unprivileged
    uid; the /plugin and /state mountpoints must exist.
    """
    missing = [str(p) for p in MOUNTPOINTS if not p.is_dir()]
    if missing:
        log.error("sandbox unavailable: missing mountpoints %s", missing)
        return False
    if not _bwrap_ok(["--ro-bind", "/", "/", "true"]):
        log.error("sandbox unavailable: `bwrap --ro-bind / / true` failed")
        return False
    if not _bwrap_ok(["--ro-bind", "/", "/", "--tmpfs", "/tmp", *_tail(PROBE_UID), "true"]):
        log.error("sandbox unavailable: bwrap cannot create pid/ipc namespaces or mount /proc")
        return False
    return True


async def _run(argv: list[str], env: dict[str, str], uid: int) -> None:
    """@brief Run one wrapped install step with a timeout; output discarded, never logged."""
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd="/",
        env=env,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        **as_user(uid),
    )
    try:
        rc = await asyncio.wait_for(proc.wait(), DEPS_TIMEOUT_S)
    except (TimeoutError, asyncio.CancelledError):
        proc.kill()
        await proc.wait()
        raise
    if rc != 0:
        log.warning("install step %s exited with status %s", argv[argv.index("--") + 1], rc)
        raise InstallError(f"deps_failed:exit={rc}")


def bwrap_runner(data_dir: Path) -> Runner:
    """
    @brief Install-step runner: bwrap as the plugin's uid with install_env() only. The
    version dir and cache are handed to the uid for the step; supervisor.start seals them.
    """

    async def run(argv: list[str], cwd: Path, uid: int | None) -> None:
        if uid is None:
            raise ValueError("install runner needs the plugin uid")
        wrapped = install_argv(argv, cwd, uid, data_dir)
        env = install_env(cwd)
        Path(env["HOME"]).mkdir(parents=True, exist_ok=True)
        chown_tree(cwd, uid)
        chown_tree(Path(env["HOME"]), uid)
        await _run(wrapped, env, uid)

    return run
