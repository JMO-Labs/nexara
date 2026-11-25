"""
@file
@brief Control-route bearer auth tests.
"""

from pathlib import Path

import httpx
import pytest

from host.main import create_app

SECRET = "s3cret-host-key"
ROUTES = [
    ("GET", "/plugins"),
    ("PUT", "/plugins/dev.nexara.echo"),
    ("DELETE", "/plugins/dev.nexara.echo"),
    ("POST", "/plugins/dev.nexara.echo/start"),
    ("POST", "/plugins/dev.nexara.echo/stop"),
    ("GET", "/plugins/dev.nexara.echo/logs"),
]


def client(tmp_path: Path, secret: str = SECRET) -> httpx.AsyncClient:
    app = create_app(secret=secret, data_dir=tmp_path)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://h")


@pytest.mark.parametrize(("method", "path"), ROUTES)
async def test_missing_bearer_401(tmp_path: Path, method: str, path: str) -> None:
    async with client(tmp_path) as c:
        r = await c.request(method, path)
    assert r.status_code == 401


@pytest.mark.parametrize(("method", "path"), ROUTES)
async def test_wrong_bearer_401(tmp_path: Path, method: str, path: str) -> None:
    async with client(tmp_path) as c:
        r = await c.request(method, path, headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


async def test_right_bearer_ok(tmp_path: Path) -> None:
    async with client(tmp_path) as c:
        r = await c.get("/plugins", headers={"Authorization": f"Bearer {SECRET}"})
    assert r.status_code == 200
    assert r.json() == []


async def test_empty_secret_rejects_everything(tmp_path: Path) -> None:
    async with client(tmp_path, secret="") as c:
        r = await c.get("/plugins", headers={"Authorization": "Bearer "})
    assert r.status_code == 401


async def test_non_bearer_scheme_401(tmp_path: Path) -> None:
    async with client(tmp_path) as c:
        r = await c.get("/plugins", headers={"Authorization": f"Basic {SECRET}"})
    assert r.status_code == 401
