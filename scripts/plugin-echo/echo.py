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
SECRET, TOKEN = E("WEBHOOK_SECRET", ""), E("NEXARA_TOKEN", "")
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


def reply(post_id: str, text: str) -> None:
    h = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
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
        if not verify(SECRET, ts, body, sig):
            self.send_response(401)
        else:
            self.send_response(204)  # 2xx once verified, even if the reply fails: no retries
            try:
                ev, did = json.loads(body), h.get("X-Nexara-Delivery", "")
                if ev["event"] == "mention" and did not in SEEN:
                    SEEN.add(did)
                    d = ev["data"]
                    reply(d["post"]["id"], f"echo: {(d.get('comment') or d['post'])['content']}")
            except Exception as exc:
                print(f"echo: reply failed: {exc}")
        self.end_headers()


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", int(E("PORT", "9100"))), Handler).serve_forever()
