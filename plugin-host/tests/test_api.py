"""
@file
@brief Control API lifecycle tests with the installer and supervisor faked.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from host import main
from host.installer import InstallError
from host.models import InstallSpec
from tests.conftest import good_tar, spec_body

SECRET = "s3cret-host-key"
AUTH = {"Authorization": f"Bearer {SECRET}"}
PID = "dev.nexara.echo"


class FakeSupervisor:
    """@brief Records start/stop calls; reports running for started plugins."""

    def __init__(self) -> None:
        self.started: dict[str, tuple[Path, InstallSpec]] = {}
        self.history: list[tuple[str, str, bool]] = []  # (version dir, spec version, v1 exists)
        self.stopped: list[str] = []
        self.fail_versions: set[str] = set()

    async def start(self, plugin_id: str, root: Path, spec: InstallSpec) -> None:
        self.history.append((root.name, spec.version, (root.parent / "1.0.0").is_dir()))
        if root.name in self.fail_versions:
            raise RuntimeError("spawn failed")
        self.started[plugin_id] = (root, spec)

    async def stop(self, plugin_id: str) -> None:
        self.started.pop(plugin_id, None)
        self.stopped.append(plugin_id)

    def status(self, plugin_id: str) -> None:
        return None

    def logs(self, plugin_id: str, lines: int) -> list[str]:
        return [f"line {i}" for i in range(lines)]


@pytest.fixture
def sup() -> FakeSupervisor:
    return FakeSupervisor()


@pytest.fixture
def app(tmp_path: Path, sup: FakeSupervisor) -> FastAPI:
    return main.create_app(secret=SECRET, data_dir=tmp_path, supervisor=sup)


@pytest.fixture
async def c(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    t = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=t, base_url="http://h", headers=AUTH) as cl:
        yield cl


def fake_install(tmp_path: Path, fail: str | None = None):  # type: ignore[no-untyped-def]
    async def _install(plugin_id: str, spec: InstallSpec, data_dir: Path, **kw: object) -> Path:
        await asyncio.sleep(0)
        if fail:
            raise InstallError(fail)
        root = data_dir / "plugins" / plugin_id / spec.version
        root.mkdir(parents=True, exist_ok=True)
        return root

    return _install


async def settle(app: FastAPI) -> None:
    while app.state.host.tasks:
        await asyncio.gather(*list(app.state.host.tasks), return_exceptions=True)


async def test_put_installs_and_starts(
    c: httpx.AsyncClient,
    app: FastAPI,
    sup: FakeSupervisor,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "install", fake_install(tmp_path))
    r = await c.put(f"/plugins/{PID}", json=spec_body(good_tar()))
    assert r.status_code == 202
    await settle(app)
    assert PID in sup.started
    assert sup.started[PID][1].env.NEXARA_TOKEN == "tok-SECRET-123"
    rows = (await c.get("/plugins")).json()
    assert rows == [
        {"id": PID, "version": "1.0.0", "status": "running", "restarts": 0, "last_error": None}
    ]


async def test_put_failure_reports_failed(
    c: httpx.AsyncClient, app: FastAPI, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(main, "install", fake_install(tmp_path, fail="sha256_mismatch"))
    await c.put(f"/plugins/{PID}", json=spec_body(good_tar()))
    await settle(app)
    row = (await c.get("/plugins")).json()[0]
    assert row["status"] == "failed" and row["last_error"] == "sha256_mismatch"


async def test_secrets_never_logged(
    c: httpx.AsyncClient,
    app: FastAPI,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    secrets: tuple[str, ...],
) -> None:
    caplog.set_level(logging.DEBUG)

    async def crash(plugin_id: str, spec: InstallSpec, data_dir: Path, **kw: object) -> Path:
        raise RuntimeError(f"boom {spec!r}")

    monkeypatch.setattr(main, "install", crash)
    await c.put(f"/plugins/{PID}", json=spec_body(good_tar()))
    await settle(app)
    assert not any(s in caplog.text for s in secrets)
    row = (await c.get("/plugins")).json()[0]
    assert row["last_error"] == "install_error"


@pytest.mark.parametrize("pid", ["Bad_ID", "nodot", "a..b", "-a.b", "a.b%00"])
async def test_bad_plugin_id_422(c: httpx.AsyncClient, pid: str) -> None:
    r = await c.put(f"/plugins/{pid}", json=spec_body(good_tar()))
    assert r.status_code == 422


async def test_delete_keeps_state_unless_purge(
    c: httpx.AsyncClient,
    app: FastAPI,
    sup: FakeSupervisor,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "install", fake_install(tmp_path))
    state = tmp_path / "plugin-state" / PID
    state.mkdir(parents=True)
    await c.put(f"/plugins/{PID}", json=spec_body(good_tar()))
    await settle(app)
    assert (await c.delete(f"/plugins/{PID}")).status_code == 204
    assert PID in sup.stopped
    assert not (tmp_path / "plugins" / PID).exists() and state.exists()
    assert (await c.get("/plugins")).json() == []
    assert (await c.delete(f"/plugins/{PID}?purge=true")).status_code == 204
    assert not state.exists()


async def test_start_stop_and_logs(
    c: httpx.AsyncClient,
    app: FastAPI,
    sup: FakeSupervisor,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert (await c.post(f"/plugins/{PID}/start")).status_code == 404
    monkeypatch.setattr(main, "install", fake_install(tmp_path))
    await c.put(f"/plugins/{PID}", json=spec_body(good_tar()))
    await settle(app)
    assert (await c.post(f"/plugins/{PID}/stop")).status_code == 204
    assert (await c.get("/plugins")).json()[0]["status"] == "stopped"
    assert (await c.post(f"/plugins/{PID}/start")).status_code == 204
    assert (await c.get("/plugins")).json()[0]["status"] == "running"
    r = await c.get(f"/plugins/{PID}/logs?lines=3")
    assert r.json() == {"lines": ["line 0", "line 1", "line 2"]}
    assert (await c.get(f"/plugins/{PID}/logs?lines=999")).status_code == 422


async def test_restart_reports_needs_config(tmp_path: Path, sup: FakeSupervisor) -> None:
    pdir = tmp_path / "plugins" / PID
    (pdir / "1.0.0").mkdir(parents=True)
    (pdir / "current").symlink_to("1.0.0")
    app = main.create_app(secret=SECRET, data_dir=tmp_path, supervisor=sup)
    t = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=t, base_url="http://h", headers=AUTH) as c:
        rows = (await c.get("/plugins")).json()
        assert rows[0]["status"] == "needs_config" and rows[0]["version"] == "1.0.0"
        assert (await c.post(f"/plugins/{PID}/start")).status_code == 409


def v(version: str) -> dict:  # type: ignore[type-arg]
    return spec_body(good_tar(version), version, entrypoint=f"main-{version}.py")


async def test_update_prunes_old_only_after_start(
    c: httpx.AsyncClient,
    app: FastAPI,
    sup: FakeSupervisor,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "install", fake_install(tmp_path))
    pdir = tmp_path / "plugins" / PID
    await c.put(f"/plugins/{PID}", json=v("1.0.0"))
    await settle(app)
    await c.put(f"/plugins/{PID}", json=v("1.1.0"))
    await settle(app)
    assert sup.history[-1] == ("1.1.0", "1.1.0", True)  # v1 still on disk during start
    assert (pdir / "current").resolve().name == "1.1.0"
    assert not (pdir / "1.0.0").exists()
    row = (await c.get("/plugins")).json()[0]
    assert (row["status"], row["version"]) == ("running", "1.1.0")


async def test_start_failure_rolls_back(
    c: httpx.AsyncClient,
    app: FastAPI,
    sup: FakeSupervisor,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "install", fake_install(tmp_path))
    pdir = tmp_path / "plugins" / PID
    await c.put(f"/plugins/{PID}", json=v("1.0.0"))
    await settle(app)
    sup.fail_versions.add("1.1.0")
    await c.put(f"/plugins/{PID}", json=v("1.1.0"))
    await settle(app)
    assert (pdir / "current").resolve().name == "1.0.0" and (pdir / "1.0.0").is_dir()
    assert not (pdir / "1.1.0").exists()
    assert sup.history[-1] == ("1.0.0", "1.0.0", True)  # old version restarted
    row = (await c.get("/plugins")).json()[0]
    assert (row["status"], row["version"], row["last_error"]) == ("failed", "1.0.0", "start_failed")


async def test_start_after_failed_update_uses_last_good_spec(
    c: httpx.AsyncClient,
    app: FastAPI,
    sup: FakeSupervisor,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "install", fake_install(tmp_path))
    await c.put(f"/plugins/{PID}", json=v("1.0.0"))
    await settle(app)
    monkeypatch.setattr(main, "install", fake_install(tmp_path, fail="deps_failed:exit=1"))
    await c.put(f"/plugins/{PID}", json=v("1.1.0"))
    await settle(app)
    row = (await c.get("/plugins")).json()[0]
    assert (row["status"], row["version"], row["last_error"]) == (
        "failed",
        "1.0.0",
        "deps_failed:exit=1",
    )
    assert (await c.post(f"/plugins/{PID}/start")).status_code == 204
    root, spec = sup.started[PID]
    assert root.name == "1.0.0" and spec.entrypoint == "main-1.0.0.py"
    assert (await c.get("/plugins")).json()[0]["status"] == "running"


async def test_superseded_put_does_not_report_old_version(
    c: httpx.AsyncClient,
    app: FastAPI,
    sup: FakeSupervisor,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate, gate2 = asyncio.Event(), asyncio.Event()
    inner = fake_install(tmp_path)

    async def gated(plugin_id: str, spec: InstallSpec, data_dir: Path, **kw: object) -> Path:
        await (gate if spec.version == "1.0.0" else gate2).wait()
        return await inner(plugin_id, spec, data_dir)

    monkeypatch.setattr(main, "install", gated)
    await c.put(f"/plugins/{PID}", json=v("1.0.0"))
    await asyncio.sleep(0.01)
    await c.put(f"/plugins/{PID}", json=v("1.1.0"))
    gate.set()
    for _ in range(50):
        if sup.history:
            break
        await asyncio.sleep(0.001)
    assert sup.history[0][1] == "1.0.0"
    row = (await c.get("/plugins")).json()[0]
    assert row["status"] == "installing"  # v1 finishing must not claim "running"
    gate2.set()
    await settle(app)
    assert [h[1] for h in sup.history] == ["1.0.0", "1.1.0"]
    row = (await c.get("/plugins")).json()[0]
    assert (row["status"], row["version"]) == ("running", "1.1.0")


async def test_queued_put_superseded_before_start_is_skipped(
    c: httpx.AsyncClient,
    app: FastAPI,
    sup: FakeSupervisor,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "install", fake_install(tmp_path))
    lock = app.state.host.locks.setdefault(PID, asyncio.Lock())
    async with lock:  # hold the per-plugin lock so both PUTs queue
        await c.put(f"/plugins/{PID}", json=v("1.0.0"))
        await c.put(f"/plugins/{PID}", json=v("1.1.0"))
    await settle(app)
    assert [h[1] for h in sup.history] == ["1.1.0"]


async def test_installs_bounded(
    c: httpx.AsyncClient, app: FastAPI, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app.state.host, "installs", asyncio.Semaphore(1))
    live = peak = 0

    async def slow(plugin_id: str, spec: InstallSpec, data_dir: Path, **kw: object) -> Path:
        nonlocal live, peak
        live += 1
        peak = max(peak, live)
        await asyncio.sleep(0.01)
        live -= 1
        root = data_dir / "plugins" / plugin_id / spec.version
        root.mkdir(parents=True)
        return root

    monkeypatch.setattr(main, "install", slow)
    for pid in ("a.one", "a.two", "a.three"):
        await c.put(f"/plugins/{pid}", json=spec_body(good_tar()))
    await settle(app)
    assert peak == 1
    assert {r["status"] for r in (await c.get("/plugins")).json()} == {"running"}


async def test_sandbox_unavailable_reported(
    c: httpx.AsyncClient,
    app: FastAPI,
    sup: FakeSupervisor,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from host.errors import SandboxUnavailableError

    seen: dict[str, object] = {}

    async def _install(plugin_id: str, spec: InstallSpec, data_dir: Path, **kw: object) -> Path:
        seen.update(kw)
        root = data_dir / "plugins" / plugin_id / spec.version
        root.mkdir(parents=True, exist_ok=True)
        return root

    async def down(*a: object) -> None:
        raise SandboxUnavailableError()

    monkeypatch.setattr(main, "install", _install)
    monkeypatch.setattr(sup, "start", down)
    await c.put(f"/plugins/{PID}", json=spec_body(good_tar()))
    await settle(app)
    assert seen["uid"] == 20000  # installs run as the plugin's uid
    row = (await c.get("/plugins")).json()[0]
    assert row["status"] == "sandbox_unavailable"
