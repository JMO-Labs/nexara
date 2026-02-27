"""
@file waf.py
@brief Lightweight Web Application Firewall middleware.

Inspects every inbound request for common attack patterns and blocks them
before they reach route handlers.  Self-hosted apps are often exposed
directly to the internet, making this especially valuable.

Design principles:
  - Fail open on ambiguous patterns — better to pass a questionable request
    than block legitimate users.
  - No body inspection — content is validated by Pydantic schemas.
  - Configurable — ``WAF_ENABLED=false`` disables the firewall entirely.
  - Observable — all blocks logged via structlog + counters in Valkey
    for admin dashboard display.
"""

from __future__ import annotations

import re
from datetime import date

import structlog
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import Settings

logger = structlog.get_logger(__name__)

_SQL_PATTERNS: re.Pattern[str] = re.compile(
    r"(union\s+select|drop\s+table|insert\s+into|delete\s+from"
    r"|exec\s*\(|xp_cmdshell|information_schema|pg_sleep|waitfor\s+delay)",
    re.IGNORECASE,
)
"""@brief Regex matching common SQL injection fragments in URLs."""

_PATH_TRAVERSAL: re.Pattern[str] = re.compile(
    r"\.\./|\.\.\\|%2e%2e%2f|%252e",
    re.IGNORECASE,
)
"""@brief Regex matching directory traversal sequences."""

_BLOCKED_UA: re.Pattern[str] = re.compile(
    r"(sqlmap|nikto|nmap|masscan|zgrab|nuclei|acunetix|burpsuite)",
    re.IGNORECASE,
)
"""@brief Regex matching known vulnerability-scanner User-Agent strings."""

_ALLOWED_METHODS: frozenset[str] = frozenset(
    {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
)
"""@brief HTTP method allowlist."""

_MAX_HEADER_SIZE: int = 8192
"""@brief Maximum total header size in bytes (8 KB)."""


class WAFMiddleware(BaseHTTPMiddleware):
    """
    @brief Lightweight WAF that inspects URL, headers, and method.

    Blocks requests matching attack signatures and records counters in
    Valkey for the admin dashboard WAF metrics panel.

    @param app The ASGI application.
    @param settings Application settings (``WAF_ENABLED`` flag).
    @param cache_client Optional Valkey cache client for block counters.
    """

    def __init__(
        self,
        app,  # type: ignore[override]
        settings: Settings,
        cache_client: Redis | None = None,
    ) -> None:
        super().__init__(app)
        self._enabled = settings.WAF_ENABLED
        self._cache = cache_client

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """@brief Inspect the request and block if a pattern matches."""
        if not self._enabled:
            return await call_next(request)

        if request.method not in _ALLOWED_METHODS:
            return await self._block(request, "INVALID_METHOD")

        url_str = str(request.url)

        if _PATH_TRAVERSAL.search(url_str):
            return await self._block(request, "PATH_TRAVERSAL")

        if _SQL_PATTERNS.search(url_str):
            return await self._block(request, "SQL_INJECTION")

        ua = request.headers.get("user-agent", "")
        if _BLOCKED_UA.search(ua):
            return await self._block(request, "BLOCKED_UA")

        total_header_size = sum(len(k) + len(v) for k, v in request.headers.items())
        if total_header_size > _MAX_HEADER_SIZE:
            return await self._block(request, "OVERSIZED_HEADERS")

        return await call_next(request)

    async def _block(self, request: Request, reason: str) -> JSONResponse:
        """
        @brief Log the block, increment the Valkey counter, and return 400.

        @param request The blocked request.
        @param reason Machine-readable reason code.
        @return A 400 JSON response with the standard error shape.
        """
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            "waf_blocked",
            ip=client_ip,
            path=str(request.url.path),
            reason=reason,
        )

        if self._cache:
            try:
                key = f"waf:blocks:{reason}:{date.today().isoformat()}"
                await self._cache.incr(key)
                await self._cache.expire(key, 86400 * 7)
            except Exception:
                logger.debug("waf_counter_increment_failed", reason=reason, exc_info=True)

        return JSONResponse(
            status_code=400,
            content={"error": {"code": "BAD_REQUEST", "message": "Blocked by WAF"}},
        )
