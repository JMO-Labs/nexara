"""
@file test_link_preview.py
@brief Unit tests for link preview service.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

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
    def test_public_url_allowed(self):
        with patch("app.services.link_preview_service.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("93.184.216.34", 0))]
            assert is_safe_url("https://example.com") is True

    def test_private_ip_rejected(self):
        with patch("app.services.link_preview_service.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("10.0.0.1", 0))]
            assert is_safe_url("https://internal.corp") is False

    def test_loopback_rejected(self):
        with patch("app.services.link_preview_service.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
            assert is_safe_url("https://localhost") is False

    def test_reserved_ip_rejected(self):
        with patch("app.services.link_preview_service.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("192.168.1.1", 0))]
            assert is_safe_url("https://router.local") is False


class TestScrapeOgMetadata:
    @pytest.mark.asyncio
    async def test_parses_og_tags(self):
        html = """
        <html><head>
        <meta property="og:title" content="Test Page">
        <meta property="og:description" content="A test description">
        <meta property="og:image" content="https://example.com/img.jpg">
        <meta property="og:site_name" content="Example">
        </head></html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.headers = {"content-type": "text/html"}

        with patch("app.services.link_preview_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await scrape_og_metadata("https://example.com")

        assert result["title"] == "Test Page"
        assert result["description"] == "A test description"
        assert result["image_url"] == "https://example.com/img.jpg"
        assert result["site_name"] == "Example"

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        with patch("app.services.link_preview_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("timeout"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await scrape_og_metadata("https://example.com")

        assert result.get("title") is None or result == {}
