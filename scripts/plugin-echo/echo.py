"""@file echo.py
@brief Nexara plugin: replies "echo: <text>" to @echo mentions."""

import hashlib
import hmac
import json
import os
import time
import urllib.request as u
from http.server import BaseHTTPRequestHandler, HTTPServer

E = os.environ.get
SECRET = E("NEXARA_WEBHOOK_SECRET") or E("WEBHOOK_SECRET", "")  # legacy name: URL mode
TOKEN = E("NEXARA_TOKEN", "")
# plugin host: one {community_id, token, webhook_secret, ...} per enabled community
COMMUNITIES = {c["community_id"]: c for c in json.loads(E("NEXARA_COMMUNITIES") or "[]")}
API = E("NEXARA_URL", "http://localhost:8000").rstrip("/")
MANIFEST = open(__file__.replace("echo.py", "nexara-plugin.toml"), "rb").read()
SEEN: set[str] = set()  # handled X-Nexara-Delivery ids (in memory)


def verify(secret: str, ts: str, body: bytes, sig: str, now: float | None = None) -> bool:
    """@brief sig == sha256=HMAC(secret, "<ts>." + body), ts within 300 s, secret set."""
    if not secret or not ts.lstrip("-").isdigit():
        return False
    mac = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256)
    fresh = abs((now or time.time()) - int(ts)) <= 300
    return fresh and hmac.compare_digest(f"sha256={mac.hexdigest()}", sig)


def creds(body: bytes) -> tuple[str, str]:
    """@brief (webhook secret, token) for the event's community; defaults otherwise."""
    try:
        c = COMMUNITIES.get(json.loads(body).get("community_id"))
    except (ValueError, AttributeError, TypeError):
        c = None
    return (c.get("webhook_secret", ""), c.get("token", "")) if c else (SECRET, TOKEN)


def reply(post_id: str, text: str, token: str = "") -> None:
    h = {"Authorization": f"Bearer {token or TOKEN}", "Content-Type": "application/json"}
    url, data = f"{API}/api/v1/posts/{post_id}/comments", json.dumps({"content": text})
    u.urlopen(u.Request(url, data.encode(), h), timeout=10).close()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(MANIFEST)

    def do_POST(self) -> None:
        h = self.headers
        body = self.rfile.read(int(h.get("Content-Length") or 0))
        ts, sig = h.get("X-Nexara-Timestamp", ""), h.get("X-Nexara-Signature", "")
        secret, token = creds(body)
        if not verify(secret, ts, body, sig):
            self.send_response(401)
        else:
            self.send_response(204)  # 2xx once verified, even if the reply fails: no retries
            try:
                ev, did = json.loads(body), h.get("X-Nexara-Delivery", "")
                if ev["event"] == "mention" and did not in SEEN:
                    SEEN.add(did)
                    d = ev["data"]
                    text = f"echo: {(d.get('comment') or d['post'])['content']}"
                    reply(d["post"]["id"], text, token)
            except Exception as exc:
                print(f"echo: reply failed: {exc}")
        self.end_headers()


if __name__ == "__main__":
    # plugin host: 127.0.0.1 (default); URL mode: HOST=0.0.0.0 so Nexara can reach it
    HTTPServer((E("HOST", "127.0.0.1"), int(E("PORT", "9100"))), Handler).serve_forever()
