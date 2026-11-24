"""
@file
@brief Process supervisor: runs each plugin under bwrap as its own uid, pumps output
       into its log ring, restarts crashes with backoff and gives up on crash loops.
"""

import asyncio
import contextlib
import logging
import os
import signal
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from host import netstat, seccomp
from host.errors import SandboxUnavailableError
from host.logs import LogBuffer, secrets_of
from host.models import Endpoint, InstallSpec, ProcStatus, Status
from host.perms import as_user, is_root, plugin_uid, prepare_state, seal_tree
from host.sandbox import bwrap_argv, plugin_env
from host.sandbox import self_test as _self_test

log = logging.getLogger(__name__)

# (plugin_id, uid, root, state, spec, seccomp_fd) -> argv
Command = Callable[[str, int, Path, Path, InstallSpec, int | None], list[str]]

BACKOFF_S = (1, 2, 4, 8, 16)
WINDOW_S = 600.0
MAX_CRASHES = 5
PORT_BASE = 9100
GRACE_S = 1.0
STOP_TIMEOUT_S = 5.0
PROC = Path("/proc")


def descendants(pid: int) -> list[int]:
    """@brief All live descendants of `pid` (from /proc/*/stat ppid links)."""
    children: dict[int, list[int]] = {}
    for d in PROC.iterdir():
        if not d.name.isdigit():
            continue
        try:
            ppid = int((d / "stat").read_text().rsplit(")", 1)[1].split()[1])
        except (OSError, IndexError, ValueError):
            continue
        children.setdefault(ppid, []).append(int(d.name))
    out, todo = [], [pid]
    while todo:
        kids = children.get(todo.pop(), [])
        out += kids
        todo += kids
    return out


@dataclass
class _Plugin:
    """@brief One supervised plugin. `env` holds secrets: memory only, never logged."""

    plugin_id: str
    argv: Callable[[int | None], list[str]]
    env: dict[str, str] = field(repr=False)
    uid: int
    run_uid: int  # uid the process really runs as (== uid when the host is root)
    port: int
    status: Status = "running"
    restarts: int = 0
    last_error: str | None = None
    crashes: deque[float] = field(default_factory=deque)
    proc: asyncio.subprocess.Process | None = None
    task: asyncio.Task[None] | None = None
    live: bool = False
    stopping: bool = False


class BwrapSupervisor:
    """@brief Supervisor implementation used by the app (see host.models.Supervisor)."""

    def __init__(
        self,
        data_dir: Path,
        *,
        command: Command | None = None,
        available: bool | None = None,
        backoff: tuple[float, ...] = BACKOFF_S,
        window: float = WINDOW_S,
        max_crashes: int = MAX_CRASHES,
        grace: float = GRACE_S,
    ) -> None:
        """
        @param command Builds the argv (default: bwrap_argv); tests swap in a plain command.
        @param available Self-test result; None = run the self-test on first use.
        @param grace A process exiting within this many seconds fails start().
        """
        self.data_dir = data_dir
        self.command = command or self._bwrap
        self._available = available
        self.backoff, self.window = backoff, window
        self.max_crashes, self.grace = max_crashes, grace
        self.plugins: dict[str, _Plugin] = {}
        self.buffers: dict[str, LogBuffer] = {}
        self.spawns: dict[str, int] = {}

    @property
    def available(self) -> bool:
        """@brief Result of the sandbox self-test (run once)."""
        if self._available is None:
            self._available = _self_test(self.data_dir)
        return self._available

    def _bwrap(
        self, pid: str, uid: int, root: Path, state: Path, spec: InstallSpec, fd: int | None
    ) -> list[str]:
        if fd is None:
            raise SandboxUnavailableError()  # never run without the seccomp filter
        return bwrap_argv(
            pid,
            uid,
            root,
            state,
            spec.runtime,
            spec.entrypoint,
            seccomp_fd=fd,
            data_dir=self.data_dir,
        )

    def _free_port(self) -> int:
        """@brief Lowest port ≥ PORT_BASE not handed out and not already listened on."""
        used = {p.port for p in self.plugins.values()} | {p for p, _ in netstat.listeners()}
        port = PORT_BASE
        while port in used:
            port += 1
        return port

    async def start(self, plugin_id: str, root: Path, spec: InstallSpec) -> None:
        """@brief (Re)start; raises if the sandbox is unavailable or the process dies at once."""
        if not self.available:
            raise SandboxUnavailableError()
        await self.stop(plugin_id)
        uid = plugin_uid(self.data_dir, plugin_id)
        state = self.data_dir / "plugin-state" / plugin_id
        prepare_state(state, uid)
        port = self._free_port()
        self.command(plugin_id, uid, root, state, spec, 0)  # validate paths before sealing
        seal_tree(root, uid)  # code + install cache: readable, never writable at runtime
        seal_tree(root.parent / ".cache", uid)

        def argv(fd: int | None) -> list[str]:
            return self.command(plugin_id, uid, root, state, spec, fd)

        run_uid = uid if is_root() else os.geteuid()
        p = _Plugin(plugin_id, argv, plugin_env(spec.env, port), uid, run_uid, port)
        buf = self.buffers.setdefault(plugin_id, LogBuffer(plugin_id))
        buf.secrets = secrets_of(spec.env)
        self.plugins[plugin_id] = p
        try:
            proc = await self._spawn(p)
            p.task = asyncio.create_task(self._watch(p, proc))
            if self.grace:
                with contextlib.suppress(TimeoutError):
                    rc = await asyncio.wait_for(asyncio.shield(proc.wait()), self.grace)
                    raise RuntimeError(f"plugin exited during start (status {rc})")
        except BaseException:
            await self.stop(plugin_id)
            raise

    async def _spawn(self, p: _Plugin) -> asyncio.subprocess.Process:
        fd = seccomp.filter_fd()
        try:
            proc = await asyncio.create_subprocess_exec(
                *p.argv(fd),
                env=p.env,
                cwd="/",
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                pass_fds=(fd,) if fd is not None else (),
                **as_user(p.uid),
            )
        finally:
            if fd is not None:
                os.close(fd)
        p.proc, p.live = proc, True
        self.spawns[p.plugin_id] = self.spawns.get(p.plugin_id, 0) + 1
        return proc

    async def _pump(self, p: _Plugin, proc: asyncio.subprocess.Process) -> None:
        buf = self.buffers[p.plugin_id]
        assert proc.stdout is not None
        while True:
            try:
                line = await proc.stdout.readline()
            except ValueError:  # line over the stream limit; asyncio already dropped it
                buf.add("[line too long, dropped]")
                continue
            if not line:
                return
            buf.add(line.decode("utf-8", "replace").rstrip("\r\n"))

    async def _watch(self, p: _Plugin, proc: asyncio.subprocess.Process) -> None:
        """@brief Pump output; on exit restart with backoff until > max_crashes in window."""
        while True:
            await self._pump(p, proc)
            rc = await proc.wait()
            p.live = False
            if p.stopping:
                return
            now = time.monotonic()
            p.crashes.append(now)
            while p.crashes and now - p.crashes[0] >= self.window:
                p.crashes.popleft()
            p.restarts += 1
            p.last_error = f"exit={rc}"
            if len(p.crashes) > self.max_crashes:
                p.status = "failed"
                log.warning("[%s] crash loop: marked failed", p.plugin_id)
                return
            delay = self.backoff[min(max(len(p.crashes), 1), len(self.backoff)) - 1]
            log.info("[%s] exited (status %s); restart in %ss", p.plugin_id, rc, delay)
            await asyncio.sleep(delay)
            if p.stopping:
                return
            try:
                proc = await self._spawn(p)
            except (OSError, SandboxUnavailableError) as e:
                p.status, p.last_error = "failed", "spawn_failed"
                log.error("[%s] respawn failed: %s", p.plugin_id, type(e).__name__)
                return

    @staticmethod
    def _signal_tree(proc: asyncio.subprocess.Process, sig: int) -> None:
        """
        @brief Signal the sandboxed processes (bwrap does not forward signals; killing it
        first would SIGKILL the plugin via --die-with-parent). No children: signal proc.
        """
        kids = descendants(proc.pid)
        for pid in kids or [proc.pid]:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(pid, sig)

    async def stop(self, plugin_id: str) -> None:
        """@brief SIGTERM the plugin, SIGKILL after 5 s, forget it; logs are kept."""
        p = self.plugins.pop(plugin_id, None)
        if p is None:
            return
        p.stopping, p.live = True, False
        proc = p.proc
        if proc is not None and proc.returncode is None:
            self._signal_tree(proc, signal.SIGTERM)
            try:
                await asyncio.wait_for(proc.wait(), STOP_TIMEOUT_S)
            except TimeoutError:
                self._signal_tree(proc, signal.SIGKILL)
                proc.kill()
                await proc.wait()
        if p.task is not None and p.task is not asyncio.current_task():
            p.task.cancel()
            await asyncio.gather(p.task, return_exceptions=True)

    def status(self, plugin_id: str) -> ProcStatus | None:
        """@brief Live state; sandbox_unavailable for every plugin if the self-test failed."""
        if self._available is False:
            return ProcStatus("sandbox_unavailable", last_error="sandbox_unavailable")
        p = self.plugins.get(plugin_id)
        return ProcStatus(p.status, p.restarts, p.last_error) if p else None

    def endpoint(self, plugin_id: str) -> Endpoint | None:
        """@brief Port/uid while the process is alive (not in crash backoff), else None."""
        p = self.plugins.get(plugin_id)
        if p and p.live and p.status == "running":
            return Endpoint(p.port, p.run_uid)
        return None

    def logs(self, plugin_id: str, lines: int) -> list[str]:
        """@brief Last `lines` redacted output lines (kept across restarts and stops)."""
        buf = self.buffers.get(plugin_id)
        return buf.tail(lines) if buf else []
