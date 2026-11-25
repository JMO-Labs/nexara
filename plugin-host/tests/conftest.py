"""
@file
@brief Shared fixtures: tarball builder and install specs.
"""

import hashlib
import io
import tarfile
from collections.abc import Callable
from typing import Any

import pytest

PKG_URL = "https://pkgs.example.com/dev.nexara.echo-1.0.0.tar.gz"


def manifest(plugin_id: str = "dev.nexara.echo", version: str = "1.0.0") -> bytes:
    """@brief Minimal nexara-plugin.toml body."""
    return (
        f'[plugin]\nid = "{plugin_id}"\nversion = "{version}"\n'
        'runtime = "python"\nentrypoint = "echo.py"\n'
    ).encode()


def make_tar(
    files: dict[str, bytes],
    extra: Callable[[tarfile.TarFile], None] | None = None,
    fmt: int = tarfile.USTAR_FORMAT,
) -> bytes:
    """@brief Build a .tar.gz from name->bytes, with an optional hook for odd members."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=fmt) as tf:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        if extra:
            extra(tf)
    return buf.getvalue()


def good_tar(version: str = "1.0.0", plugin_id: str = "dev.nexara.echo") -> bytes:
    """@brief A valid python plugin package."""
    return make_tar(
        {
            "nexara-plugin.toml": manifest(plugin_id, version),
            "echo.py": b"print('hi')\n",
            "requirements.txt": b"httpx==0.28.1\n",
        }
    )


def spec_body(data: bytes, version: str = "1.0.0", **over: Any) -> dict[str, Any]:
    """@brief PUT /plugins/{id} body for the given tarball bytes."""
    body: dict[str, Any] = {
        "version": version,
        "package_url": PKG_URL,
        "sha256": hashlib.sha256(data).hexdigest(),
        "runtime": "python",
        "entrypoint": "echo.py",
        "env": {
            "NEXARA_TOKEN": "tok-SECRET-123",
            "NEXARA_WEBHOOK_SECRET": "whs-SECRET-456",
            "NEXARA_SETTINGS": {"claude_token": "set-SECRET-789"},
            "NEXARA_COMMUNITIES": [],
        },
    }
    body.update(over)
    return body


@pytest.fixture
def secrets() -> tuple[str, ...]:
    """@brief Secret values that must never reach logs or disk."""
    return ("tok-SECRET-123", "whs-SECRET-456", "set-SECRET-789")


PUBLIC_IP = "93.184.216.34"
PKG_IP_URL = f"https://{PUBLIC_IP}/dev.nexara.echo-1.0.0.tar.gz"


@pytest.fixture(autouse=True)
def public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """@brief Resolve every hostname to one public IP (no real DNS in tests)."""
    from host import download

    async def resolve(host: str) -> list[str]:
        return [PUBLIC_IP]

    monkeypatch.setattr(download, "_resolve", resolve)
