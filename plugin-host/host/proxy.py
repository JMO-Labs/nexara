"""
@file
@brief Unauthenticated event proxy: POST /plugins/{id}/events → the plugin's
       127.0.0.1:{port}/events. The plugin verifies Nexara's HMAC itself, so the
       X-Nexara-* headers and body are passed through byte-for-byte.

Plugins share one network namespace, so before each forward every LISTEN socket on
the port must belong to the plugin's uid (else 503 port_hijacked). One shared client.
The request body is read (capped, BODY_TIMEOUT_S) before any slot is taken; then at
most MAX_INFLIGHT forwards overall and MAX_PER_PLUGIN per plugin (else 503 proxy_busy),
each under one total TIMEOUT_S deadline for send + response (else 504).
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse

from host import netstat
from host.models import PLUGIN_ID_RE, Supervisor

log = logging.getLogger(__name__)

TIMEOUT_S = 10.0
BODY_TIMEOUT_S = 10.0
MAX_BODY = 1024 * 1024
MAX_INFLIGHT = 32
MAX_PER_PLUGIN = 8
_FORWARD = (b"x-nexara-", b"content-type")

events_router = APIRouter()


class _BusyError(Exception):
    pass


class _Proxy:
    """@brief Per-app shared client + concurrency caps (created lazily on first use)."""

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=TIMEOUT_S, trust_env=False)
        self.slots = asyncio.Semaphore(MAX_INFLIGHT)
        self.per_plugin: dict[str, asyncio.Semaphore] = {}  # only ids with a live endpoint

    @contextlib.asynccontextmanager
    async def slot_for(self, plugin_id: str) -> AsyncIterator[None]:
        """@brief Take a global and a per-plugin slot without waiting; raise _BusyError if full."""
        per = self.per_plugin.setdefault(plugin_id, asyncio.Semaphore(MAX_PER_PLUGIN))
        if self.slots.locked() or per.locked():
            raise _BusyError()
        async with self.slots, per:
            yield


def _proxy(app: FastAPI) -> _Proxy:
    px: _Proxy | None = getattr(app.state, "proxy", None)
    if px is None:
        px = app.state.proxy = _Proxy()
    return px


async def close_proxy(app: FastAPI) -> None:
    """@brief Close the shared client (app shutdown)."""
    px: _Proxy | None = getattr(app.state, "proxy", None)
    if px is not None:
        await px.client.aclose()


def _err(status: int, code: str) -> JSONResponse:
    return JSONResponse({"detail": code}, status_code=status)


async def _read_capped(stream: httpx.Response | Request) -> bytes | None:
    """@brief Whole body, or None once it exceeds MAX_BODY."""
    chunks = stream.aiter_bytes() if isinstance(stream, httpx.Response) else stream.stream()
    data = bytearray()
    async for chunk in chunks:
        data += chunk
        if len(data) > MAX_BODY:
            return None
    return bytes(data)


def _owned(port: int, uid: int) -> bool:
    """@brief ≥1 listener on `port` and all of them owned by `uid`."""
    uids = netstat.listener_uids(port)
    return bool(uids) and all(u == uid for u in uids)


@events_router.post("/plugins/{plugin_id}/events")
async def proxy_events(
    plugin_id: Annotated[str, PathParam(pattern=PLUGIN_ID_RE, max_length=128)],
    request: Request,
) -> Response:
    """@brief Forward one event; 503 when the plugin is not running or not the listener."""
    supervisor: Supervisor = request.app.state.host.supervisor
    ep = supervisor.endpoint(plugin_id)
    if ep is None:
        return _err(503, "plugin_not_running")
    try:
        body = await asyncio.wait_for(_read_capped(request), BODY_TIMEOUT_S)
    except TimeoutError:
        return _err(408, "body_timeout")
    if body is None:
        return _err(413, "body_too_large")
    px = _proxy(request.app)
    try:
        async with px.slot_for(plugin_id):
            if not _owned(ep.port, ep.uid):
                log.warning("[%s] port %s not held by the plugin uid", plugin_id, ep.port)
                return _err(503, "port_hijacked")
            headers = [(k, v) for k, v in request.headers.raw if k.lower().startswith(_FORWARD)]
            fwd = _forward(px.client, ep.port, body, headers)
            status, ctype, content = await asyncio.wait_for(fwd, TIMEOUT_S)
    except _BusyError:
        return _err(503, "proxy_busy")
    except (TimeoutError, httpx.TimeoutException):
        return _err(504, "plugin_timeout")
    except httpx.HTTPError:
        return _err(503, "plugin_unreachable")
    if content is None:
        return _err(502, "plugin_response_too_large")
    return Response(content, status, media_type=ctype)


async def _forward(
    client: httpx.AsyncClient, port: int, body: bytes, headers: list[tuple[bytes, bytes]]
) -> tuple[int, str | None, bytes | None]:
    """@brief POST to the plugin; (status, content-type, capped body or None if too big)."""
    req = client.build_request(
        "POST", f"http://127.0.0.1:{port}/events", content=body, headers=headers
    )
    resp = await client.send(req, stream=True)
    try:
        return resp.status_code, resp.headers.get("content-type"), await _read_capped(resp)
    finally:
        await resp.aclose()
