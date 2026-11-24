"""
@file
@brief Event proxy tests: unauthenticated route, verbatim signature headers and body.
"""

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import respx
from fastapi import FastAPI

from host import main, netstat, proxy
from host.models import Endpoint, InstallSpec, ProcStatus

PID = "dev.nexara.echo"
UPSTREAM = "http://127.0.0.1:9107/events"
SIG = b"sha256=AbC+/=09f"  # + / = must survive untouched
BODY = b'{"type":"message.created","community_id":"c1", "x":"\xc3\xa9"}  \n'


class PortSupervisor:
    def __init__(self, port: int | None) -> None:
        self._port = port

    async def start(self, plugin_id: str, root: Path, spec: InstallSpec) -> None: ...

    async def stop(self, plugin_id: str) -> None: ...

    def status(self, plugin_id: str) -> ProcStatus | None:
        return None

    def logs(self, plugin_id: str, lines: int) -> list[str]:
        return []

    def endpoint(self, plugin_id: str) -> Endpoint | None:
        if plugin_id != PID or self._port is None:
            return None
        return Endpoint(self._port, UID)


UID = 20003
TCP_HEAD = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid\n"


def tcp_line(port: int, uid: int, state: str = "0A", ip: str = "0100007F") -> str:
    return (
        f"   0: {ip}:{port:04X} 00000000:0000 {state} 00000000:00000000 00:00000000 "
        f"00000000 {uid:>5}        0 12345 1 0000000000000000 100 0 0 10 0\n"
    )


@pytest.fixture(autouse=True)
def proc_net(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """@brief Fake /proc/net with the plugin (uid UID) listening on 9107."""
    net = tmp_path / "net"
    net.mkdir()
    (net / "tcp").write_text(TCP_HEAD + tcp_line(9107, UID) + tcp_line(9107, 0, state="01"))
    (net / "tcp6").write_text(TCP_HEAD)
    monkeypatch.setattr(netstat, "PROC_NET", net)
    return net


def make_app(tmp_path: Path, port: int | None = 9107) -> FastAPI:
    return main.create_app(secret="s", data_dir=tmp_path, supervisor=PortSupervisor(port))


@pytest.fixture
async def c(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    t = httpx.ASGITransport(app=make_app(tmp_path))
    async with httpx.AsyncClient(transport=t, base_url="http://h") as cl:
        yield cl


HEADERS = [
    (b"X-Nexara-Signature", SIG),
    (b"X-Nexara-Timestamp", b"1764000000"),
    (b"X-Nexara-Event", b"message.created"),
    (b"Content-Type", b"application/json"),
    (b"Authorization", b"Bearer leak"),
    (b"Cookie", b"a=b"),
]


@respx.mock
async def test_forwards_headers_and_body_verbatim(c: httpx.AsyncClient) -> None:
    route = respx.post(UPSTREAM).mock(return_value=httpx.Response(202, json={"ok": True}))
    r = await c.post(f"/plugins/{PID}/events", content=BODY, headers=HEADERS)
    assert r.status_code == 202 and r.json() == {"ok": True}
    sent = route.calls.last.request
    assert sent.content == BODY
    raw = {k.lower(): v for k, v in sent.headers.raw}
    assert raw[b"x-nexara-signature"] == SIG
    assert raw[b"x-nexara-timestamp"] == b"1764000000"
    assert raw[b"x-nexara-event"] == b"message.created"
    assert raw[b"content-type"] == b"application/json"
    assert b"authorization" not in raw and b"cookie" not in raw


async def test_not_running_503(tmp_path: Path) -> None:
    t = httpx.ASGITransport(app=make_app(tmp_path, port=None))
    async with httpx.AsyncClient(transport=t, base_url="http://h") as cl:
        assert (await cl.post(f"/plugins/{PID}/events", content=b"{}")).status_code == 503
    t = httpx.ASGITransport(app=make_app(tmp_path))
    async with httpx.AsyncClient(transport=t, base_url="http://h") as cl:
        r = await cl.post("/plugins/dev.nexara.unknown/events", content=b"{}")
        assert r.status_code == 503


@respx.mock
async def test_upstream_down_503_timeout_504(c: httpx.AsyncClient) -> None:
    respx.post(UPSTREAM).mock(side_effect=httpx.ConnectError("refused"))
    assert (await c.post(f"/plugins/{PID}/events", content=b"{}")).status_code == 503
    respx.post(UPSTREAM).mock(side_effect=httpx.ReadTimeout("slow"))
    assert (await c.post(f"/plugins/{PID}/events", content=b"{}")).status_code == 504


async def test_body_too_large_413(c: httpx.AsyncClient) -> None:
    r = await c.post(f"/plugins/{PID}/events", content=b"x" * (1024 * 1024 + 1))
    assert r.status_code == 413


@respx.mock
async def test_plugin_response_capped(c: httpx.AsyncClient) -> None:
    respx.post(UPSTREAM).mock(return_value=httpx.Response(200, content=b"y" * (1024 * 1024 + 1)))
    assert (await c.post(f"/plugins/{PID}/events", content=b"{}")).status_code == 502


async def test_bad_id_422_and_control_routes_still_need_auth(c: httpx.AsyncClient) -> None:
    assert (await c.post("/plugins/Bad_ID/events", content=b"{}")).status_code == 422
    assert (await c.get("/plugins")).status_code == 401


@respx.mock
@pytest.mark.parametrize(
    "tcp,tcp6",
    [
        (tcp_line(9107, 20009), ""),  # another plugin's uid holds the port
        ("", ""),  # nobody listens
        (tcp_line(9107, UID), tcp_line(9107, 20009, ip="0" * 32)),  # foreign v6 listener too
        (tcp_line(9108, UID), ""),  # plugin listens elsewhere
    ],
)
async def test_port_hijack_refused(
    c: httpx.AsyncClient, proc_net: Path, tcp: str, tcp6: str
) -> None:
    (proc_net / "tcp").write_text(TCP_HEAD + tcp)
    (proc_net / "tcp6").write_text(TCP_HEAD + tcp6)
    route = respx.post(UPSTREAM).mock(return_value=httpx.Response(202))
    r = await c.post(f"/plugins/{PID}/events", content=BODY, headers=HEADERS)
    assert r.status_code == 503 and r.json() == {"detail": "port_hijacked"}
    assert not route.called


@respx.mock
async def test_own_v6_listener_forwards(c: httpx.AsyncClient, proc_net: Path) -> None:
    (proc_net / "tcp").write_text(TCP_HEAD)
    (proc_net / "tcp6").write_text(TCP_HEAD + tcp_line(9107, UID, ip="0" * 32))
    respx.post(UPSTREAM).mock(return_value=httpx.Response(204))
    assert (await c.post(f"/plugins/{PID}/events", content=b"{}")).status_code == 204


async def test_busy_when_all_slots_taken(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(proxy, "MAX_INFLIGHT", 1)
    app = make_app(tmp_path)
    px = proxy._proxy(app)
    async with px.slots:
        t = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=t, base_url="http://h") as cl:
            r = await cl.post(f"/plugins/{PID}/events", content=b"{}")
    assert r.status_code == 503 and r.json() == {"detail": "proxy_busy"}
    assert proxy._proxy(app).client is px.client  # one shared client per app
    await proxy.close_proxy(app)


def test_netstat_parses_real_format(proc_net: Path) -> None:
    assert netstat.listeners() == [(9107, UID)]
    assert netstat.listener_uids(9107) == [UID]
    assert netstat.listener_uids(1) == []
