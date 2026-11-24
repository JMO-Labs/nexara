"""
@file
@brief Plugin host control API (bearer PLUGIN_HOST_SECRET on every control route).
"""

import asyncio
import logging
import os
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Query, Request, Response
from fastapi import Path as PathParam
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

from host.auth import require_secret
from host.deps import Runner, run_subprocess
from host.errors import SandboxUnavailableError
from host.installer import InstallError, current_version, install, prune, swap_current
from host.models import (
    PLUGIN_ID_RE,
    InstallSpec,
    PluginRecord,
    PluginRow,
    Supervisor,
)
from host.proxy import events_router
from host.sandbox import bwrap_runner, plugin_uid
from host.supervisor import BwrapSupervisor

log = logging.getLogger("plugin_host")

MAX_CONCURRENT_INSTALLS = 2
PluginId = Annotated[str, PathParam(pattern=PLUGIN_ID_RE, max_length=128)]


@dataclass
class HostState:
    """@brief Process-wide host state. Secrets live only here, in memory."""

    secret: str
    data_dir: Path
    supervisor: Supervisor
    runner: Runner = run_subprocess
    records: dict[str, PluginRecord] = field(default_factory=dict)
    tasks: set[asyncio.Task[None]] = field(default_factory=set)
    locks: dict[str, asyncio.Lock] = field(default_factory=dict)
    installs: asyncio.Semaphore = field(
        default_factory=lambda: asyncio.Semaphore(MAX_CONCURRENT_INSTALLS)
    )

    def scan(self) -> None:
        """@brief After a restart, installed plugins await env from Nexara: needs_config."""
        for cur in (self.data_dir / "plugins").glob("*/current"):
            version = current_version(cur.parent)
            if version:
                self.records[cur.parent.name] = PluginRecord(version, "needs_config")

    def pdir(self, pid: str) -> Path:
        return self.data_dir / "plugins" / pid


def _host(request: Request) -> HostState:
    state: HostState = request.app.state.host
    return state


Host = Annotated[HostState, Depends(_host)]
router = APIRouter(dependencies=[Depends(require_secret)])


def _row(host: HostState, pid: str, rec: PluginRecord) -> PluginRow:
    live = host.supervisor.status(pid) if rec.status in ("running", "stopped") else None
    if live:
        return PluginRow(
            id=pid,
            version=rec.version,
            status=live.status,
            restarts=live.restarts,
            last_error=live.last_error,
        )
    return PluginRow(id=pid, version=rec.version, status=rec.status, last_error=rec.last_error)


def _fail(rec: PluginRecord, spec: InstallSpec, code: str) -> None:
    """@brief Mark the PUT for `spec` failed unless a newer PUT superseded it."""
    if rec.pending is spec:
        rec.pending, rec.status, rec.last_error = None, "failed", code


def _sandbox_down(rec: PluginRecord, spec: InstallSpec) -> None:
    """@brief bwrap self-test failed: nothing may start."""
    if rec.pending is spec:
        rec.pending, rec.status, rec.last_error = None, "sandbox_unavailable", "sandbox_unavailable"


async def _rollback(host: HostState, pid: str, rec: PluginRecord, root: Path) -> None:
    """@brief New version failed to start: drop it and restart the last-good one."""
    if current_version(host.pdir(pid)) != root.name:
        shutil.rmtree(root, ignore_errors=True)
    if rec.spec is not None and rec.version is not None:
        try:
            await host.supervisor.start(pid, host.pdir(pid) / rec.version, rec.spec)
        except Exception as e:
            log.error("[%s] restart of previous version failed: %s", pid, type(e).__name__)


async def _install_and_start(host: HostState, pid: str, spec: InstallSpec) -> None:
    async with host.locks.setdefault(pid, asyncio.Lock()):
        rec = host.records.get(pid)
        if rec is None or rec.pending is not spec:
            return  # superseded or deleted while waiting
        try:
            async with host.installs:
                uid = plugin_uid(host.data_dir, pid)
                root = await install(pid, spec, host.data_dir, runner=host.runner, uid=uid)
        except SandboxUnavailableError:
            return _sandbox_down(rec, spec)
        except InstallError as e:
            log.warning("[%s] install failed: %s", pid, e.code)
            return _fail(rec, spec, e.code)
        except Exception as e:  # never format the exception: it may embed the spec
            log.error("[%s] install error: %s", pid, type(e).__name__)
            return _fail(rec, spec, "install_error")
        try:
            await host.supervisor.start(pid, root, spec)
        except SandboxUnavailableError:
            return _sandbox_down(rec, spec)
        except Exception as e:
            log.error("[%s] start failed: %s", pid, type(e).__name__)
            await _rollback(host, pid, rec, root)
            return _fail(rec, spec, "start_failed")
        swap_current(host.pdir(pid), spec.version)
        prune(host.pdir(pid), spec.version)
        rec.spec, rec.version = spec, spec.version
        if rec.pending is spec:
            rec.pending, rec.status, rec.last_error = None, "running", None


@router.get("/plugins")
async def list_plugins(host: Host) -> list[PluginRow]:
    """@brief Status of every known plugin."""
    return [_row(host, pid, rec) for pid, rec in sorted(host.records.items())]


@router.put("/plugins/{plugin_id}", status_code=202)
async def put_plugin(plugin_id: PluginId, spec: InstallSpec, host: Host) -> Response:
    """@brief Install/update and (re)start asynchronously; poll GET /plugins for the outcome."""
    rec = host.records.setdefault(plugin_id, PluginRecord(None, "installing"))
    rec.status, rec.pending, rec.last_error = "installing", spec, None
    task = asyncio.create_task(_install_and_start(host, plugin_id, spec))
    host.tasks.add(task)
    task.add_done_callback(host.tasks.discard)
    return Response(status_code=202)


@router.delete("/plugins/{plugin_id}", status_code=204)
async def delete_plugin(plugin_id: PluginId, host: Host, purge: bool = False) -> Response:
    """@brief Stop and remove code; keep /data/plugin-state/{id} unless purge."""
    host.records.pop(plugin_id, None)
    async with host.locks.setdefault(plugin_id, asyncio.Lock()):
        await host.supervisor.stop(plugin_id)
        shutil.rmtree(host.pdir(plugin_id), ignore_errors=True)
        if purge:
            shutil.rmtree(host.data_dir / "plugin-state" / plugin_id, ignore_errors=True)
    return Response(status_code=204)


def _get(host: HostState, pid: str) -> PluginRecord:
    rec = host.records.get(pid)
    if rec is None:
        raise HTTPException(404, "plugin_not_found")
    return rec


@router.post("/plugins/{plugin_id}/start", status_code=204)
async def start_plugin(plugin_id: PluginId, host: Host) -> Response:
    """@brief Start the last version that started OK, with its own spec and env."""
    rec = _get(host, plugin_id)
    if rec.status == "installing":
        raise HTTPException(409, "installing")
    if rec.spec is None or rec.version is None:
        raise HTTPException(409, "needs_config" if rec.version else "not_installed")
    if current_version(host.pdir(plugin_id)) != rec.version:
        raise HTTPException(409, "not_installed")
    try:
        await host.supervisor.start(plugin_id, host.pdir(plugin_id) / rec.version, rec.spec)
    except SandboxUnavailableError:
        rec.status = rec.last_error = "sandbox_unavailable"
        raise HTTPException(503, "sandbox_unavailable") from None
    rec.status, rec.last_error = "running", None
    return Response(status_code=204)


@router.post("/plugins/{plugin_id}/stop", status_code=204)
async def stop_plugin(plugin_id: PluginId, host: Host) -> Response:
    """@brief Stop a plugin (stays installed)."""
    rec = _get(host, plugin_id)
    await host.supervisor.stop(plugin_id)
    if rec.status in ("running", "failed") and rec.pending is None:
        rec.status = "stopped"
    return Response(status_code=204)


@router.get("/plugins/{plugin_id}/logs")
async def plugin_logs(
    plugin_id: PluginId, host: Host, lines: Annotated[int, Query(ge=1, le=200)] = 200
) -> dict[str, list[str]]:
    """@brief Last `lines` (≤200) output lines."""
    _get(host, plugin_id)
    return {"lines": host.supervisor.logs(plugin_id, lines)}


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    """@brief 422 without echoing input (bodies carry tokens)."""
    errs = exc.errors() if isinstance(exc, RequestValidationError) else []
    detail = [{"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in errs]
    return JSONResponse({"detail": detail}, status_code=422)


def create_app(
    secret: str | None = None,
    data_dir: Path | None = None,
    supervisor: Supervisor | None = None,
    runner: Runner | None = None,
) -> FastAPI:
    """
    @brief Build the app. Defaults come from env PLUGIN_HOST_SECRET / PLUGIN_HOST_DATA.
    An empty secret makes every control route return 401 (fail closed).
    @param supervisor Default: BwrapSupervisor (self-test runs at startup).
    @param runner Install-step runner. Default: bwrap as the plugin's uid.
    """
    secret = os.environ.get("PLUGIN_HOST_SECRET", "") if secret is None else secret
    data_dir = Path(os.environ.get("PLUGIN_HOST_DATA", "/data")) if data_dir is None else data_dir
    sup = BwrapSupervisor(data_dir) if supervisor is None else supervisor
    host = HostState(secret, data_dir, sup, runner or bwrap_runner(data_dir))
    if not secret:
        log.error("PLUGIN_HOST_SECRET is empty; all control requests will be rejected")
    host.scan()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if isinstance(sup, BwrapSupervisor):
            await asyncio.to_thread(lambda: sup.available)  # startup self-test
        yield
        for pid in list(host.records):
            await sup.stop(pid)

    app = FastAPI(
        title="Nexara plugin host",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.host = host
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.include_router(router)
    app.include_router(events_router)  # unauthenticated: the plugin verifies the HMAC
    return app


app = create_app()
