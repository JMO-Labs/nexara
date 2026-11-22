"""
@file test_link_preview_fetch_image.py
@brief fetch_image: image-only, no SVG, 5MB cap, all via safe_get.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.services.link_preview_service import IMAGE_MAX_BYTES, fetch_image
from app.services.safe_fetch import Fetched


async def test_fetch_image_ok_and_limits_passed():
    img = Fetched(url="https://cdn.example/a.png", content_type="image/png", body=b"PNG")
    with patch("app.services.link_preview_service.safe_get", AsyncMock(return_value=img)) as g:
        assert await fetch_image("https://cdn.example/a.png") == (b"PNG", "image/png")
    accept = g.await_args.kwargs["accept"]
    assert g.await_args.kwargs["max_bytes"] == IMAGE_MAX_BYTES
    assert accept("image/jpeg") and not accept("image/svg+xml") and not accept("text/html")


async def test_fetch_image_none_when_refused():
    with patch("app.services.link_preview_service.safe_get", AsyncMock(return_value=None)):
        assert await fetch_image("http://10.0.0.1/x.png") is None
