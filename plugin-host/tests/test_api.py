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
        self.stopped: list[str] = []

    async def start(self, plugin_id: str, root: Path, spec: InstallSpec) -> None:
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
    async def _install(plugin_id: str, spec: InstallSpec, data_dir: Path) -> Path:
        if fail:
            raise InstallError(fail)
        root = data_dir / "plugins" / plugin_id / spec.version
        root.mkdir(parents=True, exist_ok=True)
        (data_dir / "plugins" / plugin_id / "current").symlink_to(spec.version)
        return root

    return _install


async def settle(app: FastAPI) -> None:
    await asyncio.gather(*app.state.host.tasks.values(), return_exceptions=True)


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

    async def crash(plugin_id: str, spec: InstallSpec, data_dir: Path) -> Path:
        raise RuntimeError(f"boom {spec!r}")

    monkeypatch.setattr(main, "install", crash)
    await c.put(f"/plugins/{PID}", json=spec_body(good_tar()))
    await settle(app)
    assert not any(s in caplog.text for s in secrets)
    row = (await c.get("/plugins")).json()[0]
    assert row["last_error"] == "install_error"


async def test_bad_plugin_id_422(c: httpx.AsyncClient) -> None:
    r = await c.put("/plugins/..", json=spec_body(good_tar()))
    assert r.status_code in (404, 422)
    r = await c.put("/plugins/Bad_ID", json=spec_body(good_tar()))
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
