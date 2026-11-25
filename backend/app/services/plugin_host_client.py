"""
@file plugin_host_client.py
@brief HTTP client for the internal plugin-host control API (bearer PLUGIN_HOST_SECRET).

Request bodies carry plugin tokens and decrypted settings: they are never logged and
never included in raised errors.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from pydantic import BaseModel

from app.core.config import Settings
from app.core.exceptions import AppError

logger = structlog.get_logger(__name__)
TIMEOUT = 10.0


class HostPluginStatus(BaseModel):
    """@brief One row of the host's ``GET /plugins``."""

    id: str
    version: str | None = None
    status: str
    restarts: int = 0
    last_error: str | None = None


def _unavailable() -> AppError:
    return AppError(
        code="plugin_host_unavailable",
        message="The plugin host is not reachable. Try again in a minute.",
        status_code=503,
    )


def not_configured() -> AppError:
    """@brief Error for package mode without ``PLUGIN_HOST_URL``."""
    return AppError(
        code="plugin_host_not_configured",
        message="Package installs need the plugin host (set PLUGIN_HOST_URL)",
        status_code=422,
    )


class PluginHostClient:
    """@brief Thin async client; every host failure becomes ``plugin_host_unavailable``."""

    def __init__(
        self, base_url: str, secret: str, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {secret}"}
        self._transport = transport

    @classmethod
    def from_settings(cls, settings: Settings) -> PluginHostClient:
        """@raises AppError ``plugin_host_not_configured`` when PLUGIN_HOST_URL is empty."""
        if not settings.PLUGIN_HOST_URL:
            raise not_configured()
        return cls(settings.PLUGIN_HOST_URL, settings.PLUGIN_HOST_SECRET)

    async def _call(self, method: str, path: str, ok: tuple[int, ...], **kw: Any) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                timeout=TIMEOUT,
                follow_redirects=False,
                trust_env=False,
                transport=self._transport,
            ) as c:
                resp = await c.request(method, self._base + path, headers=self._headers, **kw)
        except httpx.HTTPError as e:
            logger.warning("plugin_host.unreachable", method=method, error=type(e).__name__)
            raise _unavailable() from None
        if resp.status_code not in ok:
            logger.warning("plugin_host.error", method=method, status=resp.status_code)
            if resp.status_code == 500 and _detail(resp) == "cleanup_failed":
                raise AppError(
                    code="plugin_host_cleanup_failed",
                    message="The plugin host could not remove the plugin files. Try again.",
                    status_code=503,
                )
            raise _unavailable()
        return resp

    async def put(self, plugin_id: str, body: dict[str, Any]) -> None:
        """@brief Install/update and (re)start; the host answers 202 and works async."""
        await self._call("PUT", f"/plugins/{plugin_id}", (200, 202), json=body)

    async def delete(self, plugin_id: str, purge: bool) -> None:
        """@brief Stop and remove code (and state when ``purge``)."""
        await self._call(
            "DELETE", f"/plugins/{plugin_id}", (204, 404), params={"purge": str(purge).lower()}
        )

    async def start(self, plugin_id: str) -> None:
        """@brief Start the last good version."""
        await self._call("POST", f"/plugins/{plugin_id}/start", (204,))

    async def stop(self, plugin_id: str) -> None:
        """@brief Stop the plugin; unknown plugins are fine."""
        await self._call("POST", f"/plugins/{plugin_id}/stop", (204, 404))

    async def status(self) -> list[HostPluginStatus]:
        """@return Status of every plugin the host knows."""
        resp = await self._call("GET", "/plugins", (200,))
        try:
            return [HostPluginStatus.model_validate(r) for r in resp.json()]
        except (ValueError, TypeError):
            raise _unavailable() from None

    async def logs(self, plugin_id: str, lines: int = 200) -> list[str]:
        """@return Last ``lines`` output lines; empty when the host does not know it."""
        resp = await self._call(
            "GET", f"/plugins/{plugin_id}/logs", (200, 404), params={"lines": lines}
        )
        if resp.status_code == 404:
            return []
        try:
            return [str(x) for x in resp.json()["lines"]]
        except (ValueError, KeyError, TypeError):
            raise _unavailable() from None


def _detail(resp: httpx.Response) -> str | None:
    try:
        d = resp.json().get("detail")
    except (ValueError, AttributeError):
        return None
    return d if isinstance(d, str) else None
