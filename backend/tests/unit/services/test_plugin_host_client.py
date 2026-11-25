"""
@file test_plugin_host_client.py
@brief PluginHostClient against a mocked host (httpx.MockTransport).
"""

from __future__ import annotations

import json
import logging

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.services.plugin_host_client import PluginHostClient


def _client(handler) -> tuple[PluginHostClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def h(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return handler(req)

    return PluginHostClient("http://host:8700/", "s3cret", httpx.MockTransport(h)), seen


async def test_put_sends_bearer_and_body():
    c, seen = _client(lambda r: httpx.Response(202))
    await c.put("dev.x.echo", {"version": "1.0.0", "env": {"NEXARA_TOKEN": "nxp_t"}})
    req = seen[0]
    assert req.method == "PUT" and str(req.url) == "http://host:8700/plugins/dev.x.echo"
    assert req.headers["authorization"] == "Bearer s3cret"
    assert json.loads(req.content)["env"]["NEXARA_TOKEN"] == "nxp_t"


async def test_status_parses_rows():
    rows = [{"id": "a.b", "version": "1.0.0", "status": "running", "restarts": 1}]
    c, _ = _client(lambda r: httpx.Response(200, json=rows))
    out = await c.status()
    assert out[0].id == "a.b" and out[0].status == "running" and out[0].last_error is None


async def test_logs_and_unknown_plugin():
    c, seen = _client(lambda r: httpx.Response(200, json={"lines": ["hi"]}))
    assert await c.logs("a.b", lines=50) == ["hi"]
    assert seen[0].url.params["lines"] == "50"
    c, _ = _client(lambda r: httpx.Response(404, json={"detail": "plugin_not_found"}))
    assert await c.logs("a.b") == []


async def test_delete_purge_param():
    c, seen = _client(lambda r: httpx.Response(204))
    await c.delete("a.b", purge=True)
    assert seen[0].method == "DELETE" and seen[0].url.params["purge"] == "true"


async def test_cleanup_failed_maps_to_retryable_error():
    c, _ = _client(lambda r: httpx.Response(500, json={"detail": "cleanup_failed"}))
    with pytest.raises(AppError) as e:
        await c.delete("a.b", purge=False)
    assert (e.value.code, e.value.status_code) == ("plugin_host_cleanup_failed", 503)


async def test_host_down_is_503_and_secret_not_logged(caplog, capsys):
    def boom(req):
        raise httpx.ConnectError("refused", request=req)

    c, _ = _client(boom)
    caplog.set_level(logging.DEBUG)
    with pytest.raises(AppError) as e:
        await c.put("a.b", {"env": {"NEXARA_TOKEN": "nxp_SECRETTOKEN"}})
    assert (e.value.code, e.value.status_code) == ("plugin_host_unavailable", 503)
    assert "nxp_SECRETTOKEN" not in caplog.text and "s3cret" not in caplog.text
    assert "nxp_SECRETTOKEN" not in str(e.value.details)
    out = capsys.readouterr()  # structlog may print directly when not configured
    assert "nxp_SECRETTOKEN" not in out.out + out.err


async def test_host_error_status_is_503():
    c, _ = _client(lambda r: httpx.Response(401))
    with pytest.raises(AppError) as e:
        await c.start("a.b")
    assert e.value.code == "plugin_host_unavailable"


def test_from_settings_requires_url():
    with pytest.raises(AppError) as e:
        PluginHostClient.from_settings(Settings(SECRET_KEY="k", PLUGIN_HOST_URL=""))
    assert (e.value.code, e.value.status_code) == ("plugin_host_not_configured", 422)
