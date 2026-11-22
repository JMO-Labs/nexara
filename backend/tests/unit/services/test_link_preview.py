"""
@file test_link_preview.py
@brief Unit tests for link preview service.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.link_preview_service import (
    MAX_URLS_PER_CONTENT,
    detect_video_provider,
    extract_urls,
    is_safe_url,
    scrape_og_metadata,
)


class TestExtractUrls:
    def test_finds_urls_in_text(self):
        text = "Check out https://example.com and http://test.org/page"
        urls = extract_urls(text)
        assert len(urls) == 2
        assert "https://example.com" in urls
        assert "http://test.org/page" in urls

    def test_ignores_code_blocks(self):
        text = "Normal https://visible.com\n```\nhttps://hidden.com\n```"
        urls = extract_urls(text)
        assert "https://visible.com" in urls
        assert "https://hidden.com" not in urls

    def test_max_10_urls(self):
        text = " ".join(f"https://example{i}.com" for i in range(15))
        urls = extract_urls(text)
        assert len(urls) == MAX_URLS_PER_CONTENT

    def test_empty_text(self):
        assert extract_urls("") == []

    def test_no_urls(self):
        assert extract_urls("Just plain text with no links") == []


class TestDetectVideoProvider:
    def test_youtube_standard(self):
        result = detect_video_provider("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result is not None
        assert result[0] == "youtube"
        assert result[1] == "dQw4w9WgXcQ"

    def test_youtube_short(self):
        result = detect_video_provider("https://youtu.be/dQw4w9WgXcQ")
        assert result is not None
        assert result[0] == "youtube"
        assert result[1] == "dQw4w9WgXcQ"

    def test_vimeo(self):
        result = detect_video_provider("https://vimeo.com/123456789")
        assert result is not None
        assert result[0] == "vimeo"
        assert result[1] == "123456789"

    def test_non_video_url(self):
        result = detect_video_provider("https://example.com/page")
        assert result is None


class TestIsSafeUrl:
    """@brief Pre-check: scheme, port and public addresses."""

    @pytest.mark.parametrize(
        ("url", "addrs", "ok"),
        [
            ("https://example.com/a", ["93.184.216.34"], True),
            ("https://intranet.example", ["10.0.0.5"], False),
            ("http://localhost/", ["127.0.0.1"], False),
            ("http://metadata.example", ["169.254.169.254"], False),
            ("http://cgnat.example", ["100.64.0.1"], False),
            ("http://mapped.example", ["::ffff:127.0.0.1"], False),
            ("http://mixed.example", ["93.184.216.34", "192.168.1.1"], False),
            ("ftp://example.com/", ["93.184.216.34"], False),
            ("https://example.com:8443/", ["93.184.216.34"], False),
            ("https://user:pw@example.com/", ["93.184.216.34"], False),
        ],
    )
    def test_rules(self, url, addrs, ok):
        with patch("app.services.link_preview_service.resolve", return_value=addrs):
            assert is_safe_url(url) is ok


class TestScrapeOgMetadata:
    """@brief OG parsing on top of safe_get."""

    async def test_parses_og_tags(self):
        from app.services.safe_fetch import Fetched

        html_doc = (
            '<meta property="og:title" content="Duck &amp; Co">'
            '<meta property="og:image" content="https://cdn.example/d.png">'
            '<meta property="og:site_name" content="Shop">'
        )
        page = Fetched(url="https://shop.example", content_type="text/html", body=html_doc.encode())
        with patch("app.services.link_preview_service.safe_get", AsyncMock(return_value=page)) as g:
            meta = await scrape_og_metadata("https://shop.example")
        assert meta == {
            "title": "Duck & Co",
            "description": None,
            "image_url": "https://cdn.example/d.png",
            "site_name": "Shop",
        }
        assert g.await_args.kwargs["max_bytes"] == 1_048_576

    async def test_returns_empty_when_fetch_refused(self):
        with patch("app.services.link_preview_service.safe_get", AsyncMock(return_value=None)):
            meta = await scrape_og_metadata("https://shop.example")
        assert set(meta.values()) == {None}
