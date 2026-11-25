"""
@file
@brief End-to-end in the image (marker `sandbox`): PUT → download → extract → deps
       (bwrap as the plugin uid) → seal → start → serve, then upgrade and purge, all as
       root WITHOUT CAP_DAC_OVERRIDE/CAP_FOWNER (the compose cap set). Catches ownership
       ordering bugs that unit tests running as a normal user cannot.
"""

import asyncio
import json
import os
import shutil
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from host import installer, main, sandbox
from host.supervisor import BwrapSupervisor
from tests.conftest import make_tar, manifest, spec_body

PID = "dev.nexara.echo"
SECRET = "e2e-secret"
AUTH = {"Authorization": f"Bearer {SECRET}"}

PLUGIN = b"""
import http.server, os
class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        open("/state/hit", "w").write(os.environ["NEXARA_TOKEN"][:3])
        self.send_response(204)
        self.end_headers()
http.server.HTTPServer(("127.0.0.1", int(os.environ["PORT"])), H).serve_forever()
"""

_CAN = (
    os.geteuid() == 0
    and shutil.which("bwrap") is not None
    and shutil.which("uv") is not None
    and all(p.is_dir() for p in sandbox.MOUNTPOINTS)
)
pytestmark = [
    pytest.mark.sandbox,
    pytest.mark.skipif(not _CAN, reason="needs root + bwrap + uv + image mountpoints"),
]


# deps that can never resolve (online or offline): the install step itself must fail
# with deps_failed — never install_error from root tripping over uid-owned dirs
BAD_REQS = b"nexara-e2e-does-not-exist==0.0.1\n"
BAD_LOCK = json.dumps(
    {
        "name": "p",
        "version": "1.0.0",
        "lockfileVersion": 3,
        "requires": True,
        "packages": {
            "": {"name": "p", "version": "1.0.0", "dependencies": {"nexara-e2e-nope": "1.0.0"}},
            "node_modules/nexara-e2e-nope": {
                "version": "1.0.0",
                "resolved": "https://registry.npmjs.org/nexara-e2e-nope/-/nexara-e2e-nope-1.0.0.tgz",
                "integrity": "sha512-" + "A" * 86 + "==",
            },
        },
    }
).encode()
BAD_PJ = b'{"name": "p", "version": "1.0.0", "dependencies": {"nexara-e2e-nope": "1.0.0"}}'


def _pkg(version: str) -> bytes:
    files = {"nexara-plugin.toml": manifest(PID, version), "echo.py": PLUGIN}
    if version == "2.0.0":
        files["requirements.txt"] = BAD_REQS
    if version == "3.0.0":
        files |= {"index.js": b"", "package.json": BAD_PJ, "package-lock.json": BAD_LOCK}
    return make_tar(files)


@pytest.fixture
async def c(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[httpx.AsyncClient]:
    monkeypatch.setenv("PLUGIN_EGRESS_FILTER", "false")
    data = Path(tempfile.mkdtemp())
    data.chmod(0o755)
    pkgs = {v: _pkg(v) for v in ("1.0.0", "1.0.1", "2.0.0", "3.0.0")}

    async def fetch(url: str) -> bytes:
        return pkgs[url.rsplit("-", 1)[1].removesuffix(".tar.gz")]

    monkeypatch.setattr(installer, "fetch", fetch)
    app = main.create_app(secret=SECRET, data_dir=data)
    t = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=t, base_url="http://h", headers=AUTH) as cl:
        cl.app = app  # type: ignore[attr-defined]
        cl.data = data  # type: ignore[attr-defined]
        cl.pkgs = pkgs  # type: ignore[attr-defined]
        yield cl
        await app.state.host.supervisor.stop(PID)
    shutil.rmtree(data, ignore_errors=True)


async def _put(c: httpx.AsyncClient, version: str, **over: str) -> dict[str, object]:
    url = f"https://pkgs.example.com/{PID}-{version}.tar.gz"
    body = spec_body(c.pkgs[version], version, package_url=url, **over)  # type: ignore[attr-defined]
    assert (await c.put(f"/plugins/{PID}", json=body)).status_code == 202
    host = c.app.state.host  # type: ignore[attr-defined]
    while host.tasks:
        await asyncio.gather(*list(host.tasks), return_exceptions=True)
    rows: list[dict[str, object]] = (await c.get("/plugins")).json()
    return rows[0]


async def _hit(c: httpx.AsyncClient) -> None:
    sup: BwrapSupervisor = c.app.state.host.supervisor  # type: ignore[attr-defined]
    port = sup.plugins[PID].port
    async with httpx.AsyncClient() as plain:
        for _ in range(50):
            try:
                r = await plain.post(f"http://127.0.0.1:{port}/events", content=b"{}")
                break
            except httpx.ConnectError:
                await asyncio.sleep(0.1)
    assert r.status_code == 204


async def test_install_start_upgrade_purge_as_root_without_dac_override(
    c: httpx.AsyncClient,
) -> None:
    data: Path = c.data  # type: ignore[attr-defined]
    row = await _put(c, "1.0.0")
    assert row["status"] == "running", row
    await _hit(c)  # 204 only after the plugin wrote /state (its own 0700 dir)

    pdir = data / "plugins" / PID
    assert (pdir / "1.0.0" / installer.SHA_MARKER).is_file()
    assert (await _put(c, "1.0.0"))["status"] == "running"  # same sha: no-op reinstall

    row = await _put(c, "1.0.1")
    assert row["status"] == "running" and row["version"] == "1.0.1", row
    assert not (pdir / "1.0.0").exists()  # sealed old version pruned
    await _hit(c)

    assert (await c.delete(f"/plugins/{PID}", params={"purge": "true"})).status_code == 204
    assert not pdir.exists() and not (data / "plugin-state" / PID).exists()


@pytest.mark.parametrize(
    ("version", "over"),
    [("2.0.0", {}), ("3.0.0", {"runtime": "node", "entrypoint": "index.js"})],
    ids=["python-requirements", "node-lockfile"],
)
async def test_dependency_failure_is_deps_failed_and_cleaned(
    c: httpx.AsyncClient, version: str, over: dict[str, str]
) -> None:
    """@brief Every runner step works as root without DAC_OVERRIDE; failure is reported
    as the step's exit code and the version dir is removed."""
    row = await _put(c, version, **over)
    assert row["status"] == "failed", row
    assert str(row["last_error"]).startswith("deps_failed:exit="), row
    data: Path = c.data  # type: ignore[attr-defined]
    assert not (data / "plugins" / PID / version).exists()
