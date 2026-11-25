"""
@file
@brief describe_error: type + errno + failing path + host frame, never the message.
"""

import logging
from pathlib import Path

import httpx
import pytest

from host import main
from host.errors import describe_error
from tests.conftest import good_tar, spec_body

SECRET = "s3cret"
PID = "dev.nexara.echo"


def _boom() -> None:
    raise PermissionError(13, "Permission denied tok-SECRET-123", "/data/plugins/x/.marker")


def test_describe_oserror_has_type_errno_path_frame_not_message() -> None:
    try:
        _boom()
    except PermissionError as e:
        out = describe_error(e)
    assert out.startswith("PermissionError errno=13 path=/data/plugins/x/.marker")
    assert "SECRET" not in out and "denied" not in out


def test_describe_names_innermost_host_frame() -> None:
    try:
        Path("/nonexistent-dir/x").read_text()
    except OSError as e:
        out = describe_error(e)
    assert "FileNotFoundError" in out and "/nonexistent-dir/x" in out
    assert " at " not in out  # no host.* frame involved


async def test_install_error_log_is_diagnosable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def install(*a: object, **kw: object) -> Path:
        _boom()
        raise AssertionError

    class Sup:
        async def stop(self, pid: str) -> None: ...

    monkeypatch.setattr(main, "install", install)
    app = main.create_app(secret=SECRET, data_dir=tmp_path, supervisor=Sup())  # type: ignore[arg-type]
    t = httpx.ASGITransport(app=app)
    hdr = {"Authorization": f"Bearer {SECRET}"}
    async with httpx.AsyncClient(transport=t, base_url="http://h", headers=hdr) as c:
        caplog.set_level(logging.ERROR)
        await c.put(f"/plugins/{PID}", json=spec_body(good_tar()))
        while app.state.host.tasks:
            await next(iter(app.state.host.tasks))
    msg = "\n".join(r.getMessage() for r in caplog.records)
    assert "install error: PermissionError errno=13 path=/data/plugins/x/.marker" in msg
    assert "SECRET" not in msg
