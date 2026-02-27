"""
@file middleware.py
@brief HTTP middleware stack: request ID, structured logging, security headers,
       and Cloudflare Access real-IP resolution.

Middleware is registered in ``main.py`` in the order defined by the backend spec.
"""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings

logger = structlog.get_logger(__name__)

REQUEST_ID_HEADER: str = "X-Request-ID"
"""@brief Header name for the correlation request identifier."""


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    @brief Attach a UUID to every request for distributed tracing.

    If the incoming request already carries an ``X-Request-ID`` header
    (e.g. set by the reverse proxy), that value is preserved.  Otherwise
    a new UUID4 is generated.  The ID is added to both the request state
    and the response headers.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    @brief Log method, path, status, and duration for every request.

    Uses ``structlog`` for JSON-formatted output that integrates with
    centralized logging systems.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else None,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    @brief Add defensive security headers to every response.

    These headers mitigate common browser-based attacks (MIME sniffing,
    click-jacking, information leakage).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        return response


class CloudflareRealIPMiddleware(BaseHTTPMiddleware):
    """
    @brief Replace the client IP with Cloudflare's ``CF-Connecting-IP`` header.

    Only activates when ``CF_ACCESS_ENABLED=true`` **and** the header is
    present.  This ensures the WAF and rate limiter see the actual user IP
    rather than a Cloudflare edge IP.

    Registered **before** the WAF and rate limiter in the middleware stack.
    """

    def __init__(self, app, settings: Settings) -> None:  # type: ignore[override]
        super().__init__(app)
        self._enabled = settings.CF_ACCESS_ENABLED

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if self._enabled:
            cf_ip = request.headers.get("CF-Connecting-IP")
            if cf_ip:
                request.scope["client"] = (cf_ip, 0)
        return await call_next(request)
