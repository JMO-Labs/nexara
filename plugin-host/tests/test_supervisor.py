"""
@file
@brief Supervisor tests with the bwrap command replaced by a plain python one-liner.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from host import netstat
from host.errors import SandboxUnavailableError
from host.logs import BURST, LogBuffer, secrets_of
from host.models import InstallSpec, PluginEnv
from host.supervisor import BwrapSupervisor
from tests.conftest import good_tar, spec_body

PID = "dev.nexara.echo"


@pytest.fixture(autouse=True)
def no_listeners(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, int]]:
    """@brief Real host sockets must not shift test ports."""
    taken: list[tuple[int, int]] = []
    monkeypatch.setattr(netstat, "listeners", lambda: taken)
    return taken


def make_sup(tmp_path: Path, script: str, **kw: object) -> BwrapSupervisor:
    def command(
        pid: str, uid: int, root: Path, state: Path, spec: InstallSpec, fd: int | None
    ) -> list[str]:
        return [sys.executable, "-c", script]

    opts: dict[str, object] = {"available": True, "backoff": (0, 0, 0, 0, 0), "grace": 0}
    opts.update(kw)
    return BwrapSupervisor(tmp_path, command=command, **opts)  # type: ignore[arg-type]


def spec() -> InstallSpec:
    return InstallSpec.model_validate(spec_body(good_tar()))


async def wait_for(cond: object, timeout: float = 10) -> None:
    async def loop() -> None:
        while not cond():  # type: ignore[operator]
            await asyncio.sleep(0.01)

    await asyncio.wait_for(loop(), timeout)


def root(tmp_path: Path) -> Path:
    r = tmp_path / "plugins" / PID / "1.0.0"
    r.mkdir(parents=True, exist_ok=True)
    return r


def port(sup: BwrapSupervisor, pid: str = PID) -> int | None:
    ep = sup.endpoint(pid)
    return ep.port if ep else None


def test_ring_keeps_last_200(capsys: pytest.CaptureFixture[str]) -> None:
    buf = LogBuffer(PID)
    t = [0.0]
    buf.clock = lambda: t[0]
    for i in range(250):
        t[0] += 1
        buf.add(f"line {i}")
    assert buf.tail(200) == [f"line {i}" for i in range(50, 250)]
    assert buf.tail(3) == ["line 247", "line 248", "line 249"]
    assert capsys.readouterr().out.splitlines()[0] == f"[{PID}] line 0"


def test_redacts_and_sanitises(capsys: pytest.CaptureFixture[str]) -> None:
    env = PluginEnv.model_validate(spec_body(good_tar())["env"])
    env.NEXARA_COMMUNITIES = json.dumps(
        [{"community_id": "c-123456789", "token": "ctok-SECRET-1", "webhook_secret": "cwhs-SEC-2"}]
    )
    buf = LogBuffer(PID)
    buf.secrets = secrets_of(env)
    buf.add("t=tok-SECRET-123 w=whs-SECRET-456 s=set-SECRET-789 c=ctok-SECRET-1 cwhs-SEC-2\x1b[2J")
    line = buf.tail(1)[0]
    for s in ("tok-SECRET-123", "whs-SECRET-456", "set-SECRET-789", "ctok-SECRET-1", "cwhs-SEC-2"):
        assert s not in line and s not in capsys.readouterr().out
    assert "\x1b" not in line
    assert "c-123456789" not in buf.secrets  # ids stay readable


def test_redacts_short_secrets() -> None:
    env = PluginEnv(NEXARA_TOKEN="k9", NEXARA_WEBHOOK_SECRET="w")
    buf = LogBuffer(PID)
    buf.secrets = secrets_of(env)
    buf.add("token=k9 secret=w")
    assert "k9" not in buf.tail(1)[0] and "=w" not in buf.tail(1)[0]


def test_rate_limit_drops_and_reports(capsys: pytest.CaptureFixture[str]) -> None:
    buf = LogBuffer(PID)
    t = [0.0]
    buf.clock = lambda: t[0]
    for i in range(BURST + 100):
        buf.add(f"flood {i}")
    assert len(capsys.readouterr().out.splitlines()) == BURST
    t[0] += 1.0  # refill
    buf.add("after")
    assert buf.tail(2) == ["[100 lines dropped: rate limit]", "after"]


async def test_runs_with_exact_env_and_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PLUGIN_HOST_SECRET", "host-secret")
    script = (
        "import os,sys,time; print(sorted(os.environ)); print(os.environ['NEXARA_TOKEN']);"
        "print('err', file=sys.stderr); sys.stdout.flush(); time.sleep(30)"
    )
    sup = make_sup(tmp_path, script)
    await sup.start(PID, root(tmp_path), spec())
    await wait_for(lambda: len(sup.logs(PID, 200)) >= 3)
    lines = sup.logs(PID, 200)
    keys = next(ln for ln in lines if "'PORT'" in ln)
    assert "PLUGIN_HOST_SECRET" not in keys and "'NEXARA_DATA_DIR'" in keys
    assert "tok-SECRET-123" not in "".join(lines) + capsys.readouterr().out
    assert "err" in lines
    st = sup.status(PID)
    assert (
        st is not None
        and st.status == "running"
        and port(sup) == 9100
        and sup.endpoint(PID).uid == (20000 if os.geteuid() == 0 else os.geteuid())
    )  # type: ignore[union-attr]
    assert (tmp_path / "plugin-state" / PID).is_dir()
    await sup.stop(PID)
    assert sup.status(PID) is None and port(sup) is None
    assert sup.logs(PID, 200) == lines  # logs survive stop


async def test_crash_loop_fails_after_sixth_crash(tmp_path: Path) -> None:
    sup = make_sup(tmp_path, "import sys; sys.exit(3)")
    await sup.start(PID, root(tmp_path), spec())
    await wait_for(lambda: sup.status(PID).status == "failed")  # type: ignore[union-attr]
    st = sup.status(PID)
    assert st is not None and st.restarts == 6 and st.last_error == "exit=3"
    assert sup.spawns[PID] == 6
    assert port(sup) is None
    await sup.stop(PID)


async def test_crashes_outside_window_do_not_fail(tmp_path: Path) -> None:
    sup = make_sup(tmp_path, "import sys; sys.exit(1)", window=0.0)
    await sup.start(PID, root(tmp_path), spec())
    await wait_for(lambda: sup.spawns.get(PID, 0) >= 10)
    assert sup.status(PID).status == "running"  # type: ignore[union-attr]
    await sup.stop(PID)


async def test_backoff_schedule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []
    real_sleep = asyncio.sleep

    async def fake_sleep(d: float) -> None:
        delays.append(d)
        await real_sleep(0)

    sup = make_sup(tmp_path, "import sys; sys.exit(1)", backoff=(1, 2, 4, 8, 16))
    monkeypatch.setattr("host.supervisor.asyncio.sleep", fake_sleep)
    await sup.start(PID, root(tmp_path), spec())
    await wait_for(lambda: sup.status(PID).status == "failed")  # type: ignore[union-attr]
    assert [d for d in delays if d >= 1] == [1, 2, 4, 8, 16]


async def test_immediate_exit_fails_start(tmp_path: Path) -> None:
    sup = make_sup(tmp_path, "import sys; sys.exit(2)", grace=5)
    with pytest.raises(RuntimeError):
        await sup.start(PID, root(tmp_path), spec())
    assert sup.status(PID) is None and port(sup) is None


async def test_ports_are_distinct_and_reused(tmp_path: Path) -> None:
    sup = make_sup(tmp_path, "import time; time.sleep(30)")
    other = "dev.nexara.other"
    r2 = tmp_path / "plugins" / other / "1.0.0"
    r2.mkdir(parents=True)
    await sup.start(PID, root(tmp_path), spec())
    await sup.start(other, r2, spec())
    assert (port(sup), port(sup, other)) == (9100, 9101)
    await sup.start(PID, root(tmp_path), spec())  # restart keeps a free port
    assert port(sup) == 9100
    await sup.stop(PID)
    await sup.stop(other)


async def test_sandbox_unavailable(tmp_path: Path) -> None:
    sup = make_sup(tmp_path, "pass", available=False)
    with pytest.raises(SandboxUnavailableError):
        await sup.start(PID, root(tmp_path), spec())
    st = sup.status(PID)
    assert st is not None and st.status == "sandbox_unavailable"


async def test_no_endpoint_during_crash_backoff(tmp_path: Path) -> None:
    sup = make_sup(tmp_path, "import sys; sys.exit(1)", backoff=(30,) * 5)
    await sup.start(PID, root(tmp_path), spec())
    await wait_for(lambda: sup.status(PID).restarts == 1)  # type: ignore[union-attr]
    assert sup.status(PID).status == "running"  # type: ignore[union-attr]
    assert sup.endpoint(PID) is None
    await sup.stop(PID)


async def test_port_skips_foreign_listener(
    tmp_path: Path, no_listeners: list[tuple[int, int]]
) -> None:
    no_listeners += [(9100, 20005), (9101, 0)]
    sup = make_sup(tmp_path, "import time; time.sleep(30)")
    await sup.start(PID, root(tmp_path), spec())
    assert port(sup) == 9102
    await sup.stop(PID)


CHILD = (
    "import signal, sys, time\n"
    "def bye(*a):\n"
    "    print('graceful', flush=True); sys.exit(0)\n"
    "signal.signal(signal.SIGTERM, bye)\n"
    "print('ready', flush=True)\n"
    "time.sleep(30)\n"
)
GRACEFUL = (  # parent ignores SIGTERM like bwrap (which does not forward it)
    "import signal, subprocess, sys\n"
    "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
    f"sys.exit(subprocess.Popen([sys.executable, '-c', {CHILD!r}]).wait())\n"
)


async def test_stop_sends_sigterm_to_sandboxed_process(tmp_path: Path) -> None:
    sup = make_sup(tmp_path, GRACEFUL)
    await sup.start(PID, root(tmp_path), spec())
    await wait_for(lambda: "ready" in sup.logs(PID, 10))
    await asyncio.wait_for(sup.stop(PID), 4)  # well under the 5 s SIGKILL fallback
    await wait_for(lambda: "graceful" in sup.logs(PID, 10), 2)


async def test_default_command_refuses_without_seccomp(tmp_path: Path) -> None:
    sup = BwrapSupervisor(tmp_path, available=True)
    r = root(tmp_path)
    with pytest.raises(SandboxUnavailableError):
        sup._bwrap(PID, 20000, r, tmp_path / "plugin-state" / PID, spec(), None)
