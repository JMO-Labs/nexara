"""
@file echo.py
@brief Minimal Nexara plugin: replies "echo: <text>" to @echo mentions (stdlib only).
"""

import hashlib
import hmac
import json
import os
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SECRET = os.environ.get("WEBHOOK_SECRET", "")
TOKEN = os.environ.get("NEXARA_TOKEN", "")
API = os.environ.get("NEXARA_URL", "http://localhost:8000").rstrip("/")
MANIFEST = Path(__file__).with_name("nexara-plugin.toml")


def verify(secret: str, ts: str, body: bytes, sig: str, now: float | None = None) -> bool:
    """@brief True if sig == sha256=HMAC(secret, "<ts>." + body) and ts is within 300 s."""
    try:
        age = abs((now if now is not None else time.time()) - int(ts))
    except ValueError:
        return False
    mac = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256)
    return age <= 300 and hmac.compare_digest(f"sha256={mac.hexdigest()}", sig)


def reply(post_id: str, text: str) -> None:
    """@brief Comment on a post as the bot, authenticated by its nxp_ token."""
    req = urllib.request.Request(
        f"{API}/api/v1/posts/{post_id}/comments",
        json.dumps({"content": text}).encode(),
        {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10).close()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        ok = self.path.endswith("nexara-plugin.toml")
        self.send_response(200 if ok else 404)
        self.end_headers()
        self.wfile.write(MANIFEST.read_bytes() if ok else b"")

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        h = self.headers
        ts, sig = h.get("X-Nexara-Timestamp", ""), h.get("X-Nexara-Signature", "")
        if not verify(SECRET, ts, body, sig):
            self.send_response(401)
        else:
            ev = json.loads(body)
            if ev["event"] == "mention":
                d = ev["data"]
                text = (d.get("comment") or d["post"]).get("content", "")
                reply(d["post"]["id"], f"echo: {text}")
            self.send_response(204)
        self.end_headers()


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 9100))), Handler).serve_forever()
