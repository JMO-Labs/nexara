"""
@file
@brief Unauthenticated event proxy: POST /plugins/{id}/events → the plugin's
       127.0.0.1:{port}/events. The plugin verifies Nexara's HMAC itself, so the
       X-Nexara-* headers and body are passed through byte-for-byte.

Plugins share one network namespace, so before each forward every LISTEN socket on
the port must belong to the plugin's uid (else 503 port_hijacked). One shared client;
at most MAX_INFLIGHT concurrent forwards (else 503 proxy_busy).
"""

import asyncio
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse

from host import netstat
from host.models import PLUGIN_ID_RE, Supervisor

log = logging.getLogger(__name__)

TIMEOUT_S = 10.0
MAX_BODY = 1024 * 1024
MAX_INFLIGHT = 32
_FORWARD = (b"x-nexara-", b"content-type")

events_router = APIRouter()


class _Proxy:
    """@brief Per-app shared client + concurrency cap (created lazily on first use)."""

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=TIMEOUT_S, trust_env=False)
        self.slots = asyncio.Semaphore(MAX_INFLIGHT)


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
    px = _proxy(request.app)
    if px.slots.locked():
        return _err(503, "proxy_busy")
    async with px.slots:
        body = await _read_capped(request)
        if body is None:
            return _err(413, "body_too_large")
        if not _owned(ep.port, ep.uid):
            log.warning("[%s] port %s not held by the plugin uid: refusing", plugin_id, ep.port)
            return _err(503, "port_hijacked")
        headers = [(k, v) for k, v in request.headers.raw if k.lower().startswith(_FORWARD)]
        req = px.client.build_request(
            "POST", f"http://127.0.0.1:{ep.port}/events", content=body, headers=headers
        )
        try:
            resp = await px.client.send(req, stream=True)
            try:
                content = await _read_capped(resp)
            finally:
                await resp.aclose()
        except httpx.TimeoutException:
            return _err(504, "plugin_timeout")
        except httpx.HTTPError:
            return _err(503, "plugin_unreachable")
    if content is None:
        return _err(502, "plugin_response_too_large")
    return Response(content, resp.status_code, media_type=resp.headers.get("content-type"))
