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


def test_timeout_is_5s():
    assert svc.HTTP_TIMEOUT == 5.0
