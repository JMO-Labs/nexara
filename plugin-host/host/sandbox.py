"""
@file
@brief bubblewrap sandbox: argv builders for plugin processes and dependency installs,
       plugin env, resource limits and the startup self-test.

Every plugin sees a read-only host root with `/data` masked by a tmpfs, its own code
read-only at /plugin and its state read-write at /state. /proc is the container's
(masked) /proc inherited through `--ro-bind / /`: a fresh `--proc` would need docker
`systempaths=unconfined`, which lets a compromised host write /proc/sys (decided: no).
The pid namespace still hides/blocks other processes (signals ESRCH; environ/fd EACCES
by uid). Nested user namespaces etc. are blocked by the seccomp filter (host.seccomp).
The image must provide the empty mountpoints /plugin and /state.
"""

import asyncio
import logging
import os
import subprocess
from pathlib import Path

from host import perms, seccomp
from host.deps import DEPS_TIMEOUT_S, Runner, install_env
from host.errors import InstallError, SandboxUnavailableError
from host.models import PluginEnv
from host.perms import PROBE_UID, chown_tree, seal_tree

log = logging.getLogger(__name__)

BWRAP = "bwrap"
PRLIMIT = "prlimit"
MOUNTPOINTS = (Path("/plugin"), Path("/state"))
PLUGIN_PATH = "/usr/local/bin:/usr/bin:/bin"
_NS_FLAGS = ["--unshare-pid", "--unshare-ipc", "--die-with-parent", "--new-session"]
MIB = 1024 * 1024
# env var -> (prlimit option, default, unit multiplier). No RLIMIT_AS: V8 reserves large
# virtual ranges (WebAssembly, so Node's fetch/undici); memory is capped by the container.
LIMITS = {
    "PLUGIN_LIMIT_NPROC": ("--nproc", 256, 1),
    "PLUGIN_LIMIT_FSIZE_MB": ("--fsize", 1024, MIB),
    "PLUGIN_LIMIT_NOFILE": ("--nofile", 1024, 1),
}
TMPFS_ENV, TMPFS_DEFAULT_MB = "PLUGIN_TMPFS_MB", 64
INSECURE_ENV = "PLUGIN_HOST_INSECURE_DEV"


def _env_int(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, default))
    except ValueError:
        return default
    return value if value > 0 else default


def limits_prefix() -> list[str]:
    """@brief `prlimit --nproc=… --fsize=… --nofile=…` (RLIMIT_NPROC is per uid)."""
    opts = [f"{opt}={_env_int(env, d) * mult}" for env, (opt, d, mult) in LIMITS.items()]
    return [PRLIMIT, *opts]


def _tmpfs(path: str) -> list[str]:
    return ["--size", str(_env_int(TMPFS_ENV, TMPFS_DEFAULT_MB) * MIB), "--tmpfs", path]


def _within(path: Path, parent: Path) -> Path:
    """@brief Resolve `path` (following symlinks) and require it to be directly in `parent`."""
    real = path.resolve()
    if real.parent != parent.resolve():
        raise ValueError("path outside the plugin's own directory")
    return real


def _common(data_dir: Path) -> list[str]:
    """@brief Limits, read-only root, private sized /tmp, host data masked."""
    return [
        *limits_prefix(), BWRAP,
        "--ro-bind", "/", "/",
        *_tmpfs("/tmp"),
        *_tmpfs(str(data_dir)),
    ]  # fmt: skip


def _tail(uid: int, seccomp_fd: int) -> list[str]:
    """@brief /dev, private pid/ipc namespaces, uid/gid inside, no caps, seccomp filter."""
    return [
        "--dev", "/dev",
        *_tmpfs("/dev/shm"),  # --dev's own /dev/shm is unsized
        *_NS_FLAGS,
        "--unshare-user", "--uid", str(uid), "--gid", str(uid),
        "--cap-drop", "ALL",
        "--seccomp", str(seccomp_fd),
    ]  # fmt: skip


def bwrap_argv(
    plugin_id: str,
    uid: int,
    root: Path,
    state: Path,
    runtime: str,
    entrypoint: str,
    *,
    seccomp_fd: int,
    data_dir: Path = Path("/data"),
) -> list[str]:
    """
    @brief Full argv to run a plugin under bwrap. Code is read-only, the install cache is
    never mounted; only /state is writable.
    @param root Version dir; must resolve to <data>/plugins/<plugin_id>/<version>.
    @param state Must resolve to <data>/plugin-state/<plugin_id>.
    @param seccomp_fd fd holding the BPF filter (see host.seccomp.filter_fd).
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
        *_tail(uid, seccomp_fd),
        "--remount-ro", str(data_dir),
        "--chdir", "/plugin",
        "--", *cmd,
    ]  # fmt: skip


def install_argv(
    argv: list[str], cwd: Path, uid: int, data_dir: Path, *, seccomp_fd: int
) -> list[str]:
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
        *_tail(uid, seccomp_fd),
        "--remount-ro", str(data_dir),
        "--chdir", str(cwd),
        "--", *argv,
    ]  # fmt: skip


def plugin_env(env: PluginEnv, port: int) -> dict[str, str]:
    """@brief The plugin's entire process env: NEXARA_* + PORT + minimal PATH/HOME."""
    out = {k: v for k, v in env.model_dump().items() if v is not None}
    # host env wins: it is what the egress filter allowlists (a pushed URL is a fallback)
    url = os.environ.get("NEXARA_URL") or out.get("NEXARA_URL")
    out.pop("NEXARA_URL", None)
    if url:
        out = {"NEXARA_URL": url, **out}
    out.update(NEXARA_DATA_DIR="/state", PORT=str(port), PATH=PLUGIN_PATH, HOME="/tmp")
    return out


def _probe(argv: list[str], fd: int | None = None) -> bool:
    """@brief Run a probe as PROBE_UID; closes `fd` (the seccomp pipe) if given."""
    try:
        proc = subprocess.run(
            argv,
            env={"PATH": PLUGIN_PATH},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=10,
            pass_fds=(fd,) if fd is not None else (),
            **perms.as_user(PROBE_UID),
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        if fd is not None:
            os.close(fd)


def self_test(data_dir: Path = Path("/data")) -> bool:
    """
    @brief Mountpoints exist; `bwrap --ro-bind / / true`; then the exact limits,
    namespaces, tmpfs sizes and seccomp filter plugins use — as an unprivileged uid.
    """
    if not perms.is_root():
        if os.environ.get(INSECURE_ENV, "").lower() != "true":
            log.error("sandbox unavailable: host is not root (no per-plugin uids)")
            return False
        log.warning(
            "INSECURE: %s=true — plugins run as the host's own uid, NOT isolated from "
            "each other or the host's files. Development only.",
            INSECURE_ENV,
        )
    missing = [str(p) for p in MOUNTPOINTS if not p.is_dir()]
    if missing:
        log.error("sandbox unavailable: missing mountpoints %s", missing)
        return False
    if not _probe([BWRAP, "--ro-bind", "/", "/", "true"]):
        log.error("sandbox unavailable: `bwrap --ro-bind / / true` failed")
        return False
    fd = seccomp.filter_fd()
    if fd is None:
        log.error("sandbox unavailable: no seccomp filter")
        return False
    if not _probe([*_common(data_dir), *_tail(PROBE_UID, fd), "true"], fd):
        log.error("sandbox unavailable: bwrap cannot apply namespaces/limits/seccomp")
        return False
    return True


async def _run(argv: list[str], env: dict[str, str], uid: int, fd: int) -> None:
    """@brief Run one wrapped install step with a timeout; output discarded, never logged."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd="/",
            env=env,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            pass_fds=(fd,),
            **perms.as_user(uid),
        )
    finally:
        os.close(fd)
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
    version dir and cache are handed to the uid for the step and sealed back to root
    after it (success or not), so root can write between steps without DAC_OVERRIDE.
    """

    async def run(argv: list[str], cwd: Path, uid: int | None) -> None:
        if uid is None:
            raise ValueError("install runner needs the plugin uid")
        fd = seccomp.filter_fd()
        if fd is None:
            raise SandboxUnavailableError()
        try:
            wrapped = install_argv(argv, cwd, uid, data_dir, seccomp_fd=fd)
            env = install_env(cwd)
            Path(env["HOME"]).mkdir(parents=True, exist_ok=True)
            chown_tree(cwd, uid)
            chown_tree(Path(env["HOME"]), uid)
        except BaseException:
            os.close(fd)
            raise
        try:
            await _run(wrapped, env, uid, fd)
        finally:  # root lacks DAC_OVERRIDE: take both trees back before it writes there
            await asyncio.to_thread(seal_tree, cwd, uid)
            await asyncio.to_thread(seal_tree, Path(env["HOME"]), uid)

    return run
