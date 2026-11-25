"""
@file test_echo_example.py
@brief The echo example: verify() agrees with core signing; reply() and the
       per-community secret/token selection work against a fake API.
"""

import importlib.util
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.plugins.signing import sign

_p = Path(__file__).resolve().parents[4] / "scripts" / "plugin-echo" / "echo.py"
_spec = importlib.util.spec_from_file_location("plugin_echo", _p)
assert _spec and _spec.loader
echo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(echo)

BODY = b'{"event":"mention"}'


def test_accepts_core_signature() -> None:
    assert echo.verify("s", "1000", BODY, sign("s", 1000, BODY), now=1100)


def test_rejects_tamper_wrong_secret_and_stale() -> None:
    sig = sign("s", 1000, BODY)
    assert not echo.verify("s", "1000", BODY + b" ", sig, now=1000)
    assert not echo.verify("x", "1000", BODY, sig, now=1000)
    assert not echo.verify("s", "1000", BODY, sig, now=1301)
    assert not echo.verify("s", "bad", BODY, sig, now=1000)


def test_empty_secret_fails_closed() -> None:
    assert not echo.verify("", "1000", BODY, sign("", 1000, BODY), now=1000)


class _FakeApi(BaseHTTPRequestHandler):
    """@brief Records each comment POST (path, auth header, body)."""

    calls: list[tuple[str, str, dict[str, Any]]] = []

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.calls.append((self.path, self.headers.get("Authorization", ""), body))
        self.send_response(201)
        self.end_headers()

    def log_message(self, *a: Any) -> None:
        pass


def _serve(handler: type[BaseHTTPRequestHandler]) -> HTTPServer:
    srv = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _load(monkeypatch: pytest.MonkeyPatch, api: HTTPServer, **env: str) -> Any:
    monkeypatch.setenv("NEXARA_URL", f"http://127.0.0.1:{api.server_port}")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    spec = importlib.util.spec_from_file_location("plugin_echo_live", _p)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_reply_posts_comment_with_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeApi.calls = []
    api = _serve(_FakeApi)
    try:
        mod = _load(monkeypatch, api, NEXARA_TOKEN="nxp_default")
        mod.reply("p1", "echo: hi")
    finally:
        api.shutdown()
    assert _FakeApi.calls == [
        ("/api/v1/posts/p1/comments", "Bearer nxp_default", {"content": "echo: hi"})
    ]


def test_mention_in_second_community_uses_its_secret_and_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeApi.calls = []
    api = _serve(_FakeApi)
    comms = [
        {"community_id": "c1", "token": "tok1", "webhook_secret": "s1"},
        {"community_id": "c2", "token": "tok2", "webhook_secret": "s2"},
    ]
    mod = _load(
        monkeypatch,
        api,
        NEXARA_TOKEN="tok1",
        NEXARA_WEBHOOK_SECRET="s1",
        NEXARA_COMMUNITIES=json.dumps(comms),
    )
    plugin = _serve(mod.Handler)
    ev = {
        "event": "mention",
        "community_id": "c2",
        "data": {"post": {"id": "p9", "content": "@echo yo"}},
    }
    body = json.dumps(ev).encode()
    ts = int(time.time())
    try:
        r = httpx.post(
            f"http://127.0.0.1:{plugin.server_port}/events",
            content=body,
            headers={
                "X-Nexara-Timestamp": str(ts),
                "X-Nexara-Signature": sign("s2", ts, body),
                "X-Nexara-Delivery": "d1",
            },
        )
    finally:
        plugin.shutdown()
        api.shutdown()
    assert r.status_code == 204
    assert _FakeApi.calls == [
        ("/api/v1/posts/p9/comments", "Bearer tok2", {"content": "echo: @echo yo"})
    ]


def test_community_entry_without_creds_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """@brief A malformed NEXARA_COMMUNITIES entry gives 401, never an unhandled error."""
    api = _serve(_FakeApi)
    mod = _load(monkeypatch, api, NEXARA_COMMUNITIES=json.dumps([{"community_id": "c3"}]))
    assert mod.creds(b'{"community_id": "c3"}') == ("", "")
    plugin = _serve(mod.Handler)
    body = b'{"event": "mention", "community_id": "c3", "data": {}}'
    try:
        r = httpx.post(
            f"http://127.0.0.1:{plugin.server_port}/events",
            content=body,
            headers={"X-Nexara-Timestamp": "1", "X-Nexara-Signature": sign("", 1, body)},
        )
    finally:
        plugin.shutdown()
        api.shutdown()
    assert r.status_code == 401
