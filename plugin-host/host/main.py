"""
@file
@brief Plugin host control API (bearer PLUGIN_HOST_SECRET on every control route).
"""

import asyncio
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Query, Request, Response
from fastapi import Path as PathParam
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

from host.auth import require_secret
from host.installer import InstallError, install
from host.models import (
    PLUGIN_ID_RE,
    InstallSpec,
    NullSupervisor,
    PluginRecord,
    PluginRow,
    Supervisor,
)

log = logging.getLogger("plugin_host")

PluginId = Annotated[str, PathParam(pattern=PLUGIN_ID_RE, max_length=128)]


@dataclass
class HostState:
    """@brief Process-wide host state. Secrets live only here, in memory."""

    secret: str
    data_dir: Path
    supervisor: Supervisor
    records: dict[str, PluginRecord] = field(default_factory=dict)
    tasks: dict[str, asyncio.Task[None]] = field(default_factory=dict)
    locks: dict[str, asyncio.Lock] = field(default_factory=dict)

    def scan(self) -> None:
        """@brief After a restart, installed plugins await env from Nexara: needs_config."""
        for cur in (self.data_dir / "plugins").glob("*/current"):
            if cur.is_symlink() and cur.exists():
                self.records[cur.parent.name] = PluginRecord(cur.resolve().name, "needs_config")


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


async def _install_and_start(host: HostState, pid: str, spec: InstallSpec) -> None:
    lock = host.locks.setdefault(pid, asyncio.Lock())
    async with lock:
        rec = host.records.get(pid)
        if rec is None or rec.spec is not spec:
            return  # superseded or deleted while waiting
        try:
            root = await install(pid, spec, host.data_dir)
            await host.supervisor.start(pid, root, spec)
            rec.version, rec.status, rec.last_error = spec.version, "running", None
        except InstallError as e:
            rec.status, rec.last_error = "failed", e.code
            log.warning("[%s] install failed: %s", pid, e.code)
        except Exception as e:  # never format the exception: it may embed the spec
            rec.status, rec.last_error = "failed", "install_error"
            log.error("[%s] install error: %s", pid, type(e).__name__)


@router.get("/plugins")
async def list_plugins(host: Host) -> list[PluginRow]:
    """@brief Status of every known plugin."""
    return [_row(host, pid, rec) for pid, rec in sorted(host.records.items())]


@router.put("/plugins/{plugin_id}", status_code=202)
async def put_plugin(plugin_id: PluginId, spec: InstallSpec, host: Host) -> Response:
    """@brief Install/update and (re)start asynchronously; poll GET /plugins for the outcome."""
    rec = host.records.setdefault(plugin_id, PluginRecord(None, "installing"))
    rec.status, rec.spec, rec.last_error = "installing", spec, None
    task = asyncio.create_task(_install_and_start(host, plugin_id, spec))
    host.tasks[plugin_id] = task
    task.add_done_callback(
        lambda t: host.tasks.pop(plugin_id, None) if host.tasks.get(plugin_id) is t else None
    )
    return Response(status_code=202)


@router.delete("/plugins/{plugin_id}", status_code=204)
async def delete_plugin(plugin_id: PluginId, host: Host, purge: bool = False) -> Response:
    """@brief Stop and remove code; keep /data/plugin-state/{id} unless purge."""
    host.records.pop(plugin_id, None)
    async with host.locks.setdefault(plugin_id, asyncio.Lock()):
        await host.supervisor.stop(plugin_id)
        shutil.rmtree(host.data_dir / "plugins" / plugin_id, ignore_errors=True)
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
    """@brief Start an installed plugin with its in-memory env."""
    rec = _get(host, plugin_id)
    current = host.data_dir / "plugins" / plugin_id / "current"
    if rec.spec is None or rec.status == "installing" or not current.exists():
        raise HTTPException(409, "needs_config" if rec.spec is None else "not_installed")
    await host.supervisor.start(plugin_id, current.resolve(), rec.spec)
    rec.status, rec.last_error = "running", None
    return Response(status_code=204)


@router.post("/plugins/{plugin_id}/stop", status_code=204)
async def stop_plugin(plugin_id: PluginId, host: Host) -> Response:
    """@brief Stop a plugin (stays installed)."""
    rec = _get(host, plugin_id)
    await host.supervisor.stop(plugin_id)
    if rec.status == "running":
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
) -> FastAPI:
    """
    @brief Build the app. Defaults come from env PLUGIN_HOST_SECRET / PLUGIN_HOST_DATA.
    An empty secret makes every control route return 401 (fail closed).
    """
    secret = os.environ.get("PLUGIN_HOST_SECRET", "") if secret is None else secret
    data_dir = Path(os.environ.get("PLUGIN_HOST_DATA", "/data")) if data_dir is None else data_dir
    host = HostState(secret, data_dir, supervisor or NullSupervisor())
    if not secret:
        log.error("PLUGIN_HOST_SECRET is empty; all control requests will be rejected")
    host.scan()
    app = FastAPI(title="Nexara plugin host", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.host = host
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.include_router(router)
    return app


app = create_app()
