"""
@file
@brief Unauthenticated event proxy: POST /plugins/{id}/events → the plugin's
       127.0.0.1:{port}/events. The plugin verifies Nexara's HMAC itself, so the
       X-Nexara-* headers and body are passed through byte-for-byte.
"""

from typing import Annotated

import httpx
from fastapi import APIRouter, Request, Response
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse

from host.models import PLUGIN_ID_RE, Supervisor

TIMEOUT_S = 10.0
MAX_BODY = 1024 * 1024
_FORWARD = (b"x-nexara-", b"content-type")

events_router = APIRouter()


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


@events_router.post("/plugins/{plugin_id}/events")
async def proxy_events(
    plugin_id: Annotated[str, PathParam(pattern=PLUGIN_ID_RE, max_length=128)],
    request: Request,
) -> Response:
    """@brief Forward one event; 503 when the plugin is not running."""
    supervisor: Supervisor = request.app.state.host.supervisor
    port = supervisor.port(plugin_id)
    if port is None:
        return _err(503, "plugin_not_running")
    body = await _read_capped(request)
    if body is None:
        return _err(413, "body_too_large")
    headers = [(k, v) for k, v in request.headers.raw if k.lower().startswith(_FORWARD)]
    async with httpx.AsyncClient(timeout=TIMEOUT_S, trust_env=False) as client:
        try:
            req = client.build_request(
                "POST", f"http://127.0.0.1:{port}/events", content=body, headers=headers
            )
            resp = await client.send(req, stream=True)
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
