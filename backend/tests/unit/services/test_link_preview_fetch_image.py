"""
@file test_link_preview_fetch_image.py
@brief Tests for SSRF-safe image fetching used by the image proxy.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from app.services import link_preview_service as svc


@pytest.mark.asyncio
async def test_fetch_image_rejects_private():
    assert await svc.fetch_image("http://10.0.0.1/a.png") is None


@pytest.mark.asyncio
async def test_fetch_image_rejects_loopback():
    assert await svc.fetch_image("http://localhost/a.png") is None


@pytest.mark.asyncio
async def test_fetch_image_ok():
    def handler(request):
        return httpx.Response(200, content=b"img", headers={"content-type": "image/png"})

    transport = httpx.MockTransport(handler)
    with (
        patch.object(svc, "is_safe_url", return_value=True),
        patch.object(svc, "_client_kwargs", return_value={"transport": transport}),
    ):
        assert await svc.fetch_image("https://x.example/a.png") == (b"img", "image/png")


@pytest.mark.asyncio
async def test_fetch_image_rejects_non_image():
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, content=b"<html>", headers={"content-type": "text/html"})
    )
    with (
        patch.object(svc, "is_safe_url", return_value=True),
        patch.object(svc, "_client_kwargs", return_value={"transport": transport}),
    ):
        assert await svc.fetch_image("https://x.example/a") is None


@pytest.mark.asyncio
async def test_fetch_image_rejects_oversize():
    big = b"0" * (svc.IMAGE_MAX_BYTES + 1)
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, content=big, headers={"content-type": "image/png"})
    )
    with (
        patch.object(svc, "is_safe_url", return_value=True),
        patch.object(svc, "_client_kwargs", return_value={"transport": transport}),
    ):
        assert await svc.fetch_image("https://x.example/a.png") is None


@pytest.mark.asyncio
async def test_fetch_image_stops_reading_oversize_stream():
    """No Content-Length: read must stop once the cap is exceeded."""
    chunk = b"0" * 65536
    sent = {"bytes": 0}

    async def body():
        while sent["bytes"] < svc.IMAGE_MAX_BYTES * 4:
            sent["bytes"] += len(chunk)
            yield chunk

    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, content=body(), headers={"content-type": "image/png"})
    )
    with (
        patch.object(svc, "is_safe_url", return_value=True),
        patch.object(svc, "_client_kwargs", return_value={"transport": transport}),
    ):
        assert await svc.fetch_image("https://x.example/a.png") is None
    assert sent["bytes"] <= svc.IMAGE_MAX_BYTES + 2 * len(chunk)


@pytest.mark.asyncio
async def test_fetch_image_rejects_oversize_content_length_without_reading():
    read = {"started": False}

    async def body():
        read["started"] = True
        yield b"img"

    headers = {"content-type": "image/png", "content-length": str(svc.IMAGE_MAX_BYTES + 1)}
    transport = httpx.MockTransport(lambda r: httpx.Response(200, content=body(), headers=headers))
    with (
        patch.object(svc, "is_safe_url", return_value=True),
        patch.object(svc, "_client_kwargs", return_value={"transport": transport}),
    ):
        assert await svc.fetch_image("https://x.example/a.png") is None
    assert read["started"] is False


def test_timeout_is_5s():
    assert svc.HTTP_TIMEOUT == 5.0


def test_client_kwargs_disables_redirects():
    assert svc._client_kwargs() == {"timeout": svc.HTTP_TIMEOUT, "follow_redirects": False}


@pytest.mark.asyncio
async def test_fetch_image_returns_none_on_http_error():
    transport = httpx.MockTransport(lambda r: httpx.Response(500))
    with (
        patch.object(svc, "is_safe_url", return_value=True),
        patch.object(svc, "_client_kwargs", return_value={"transport": transport}),
    ):
        assert await svc.fetch_image("https://x.example/a.png") is None
