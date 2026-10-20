"""
@file link_preview_service.py
@brief OG link preview scraping with SSRF protection.
"""

from __future__ import annotations

import hashlib
import ipaddress
import re
import socket
import uuid
from urllib.parse import urlparse

import httpx

from app.repositories.link_preview_repo import LinkPreviewRepository

URL_PATTERN = re.compile(
    r"https?://[^\s<>\"')\]]+",
    re.IGNORECASE,
)
"""@brief Regex for detecting URLs in text."""

VIDEO_PROVIDERS: dict[str, re.Pattern[str]] = {
    "youtube": re.compile(
        r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})",
        re.IGNORECASE,
    ),
    "vimeo": re.compile(
        r"vimeo\.com/(?:video/)?(\d+)",
        re.IGNORECASE,
    ),
    "twitch": re.compile(
        r"twitch\.tv/(?:videos/)?(\d+)",
        re.IGNORECASE,
    ),
    "peertube": re.compile(
        r"peertube\.(?:tv|local|social)/(?:videos/watch/)?([a-zA-Z0-9_-]+)",
        re.IGNORECASE,
    ),
    "dailymotion": re.compile(
        r"dailymotion\.com/video/([a-zA-Z0-9]+)",
        re.IGNORECASE,
    ),
}
"""@brief Provider name -> regex for extracting video ID."""

MAX_URLS_PER_CONTENT = 10
"""@brief Maximum URLs to extract and scrape per post/message."""

CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)
"""@brief Matches fenced code blocks to exclude from URL extraction."""

HTTP_TIMEOUT = 5.0
"""@brief HTTP request timeout in seconds."""

HTTP_MAX_BYTES = 1_048_576
"""@brief Maximum response body size (1MB)."""


def extract_urls(text: str) -> list[str]:
    """
    @brief Extract URLs from text, skipping code blocks, max 10.

    @param text Content to scan for URLs.
    @return List of unique URLs, up to MAX_URLS_PER_CONTENT.
    """
    if not text or not text.strip():
        return []

    # Remove code blocks before extracting URLs
    without_code = CODE_BLOCK_PATTERN.sub("", text)
    matches = URL_PATTERN.findall(without_code)

    seen: set[str] = set()
    result: list[str] = []
    for url in matches:
        # Strip trailing punctuation that might have been captured
        url = url.rstrip(".,;:!?)")
        if url not in seen and len(result) < MAX_URLS_PER_CONTENT:
            seen.add(url)
            result.append(url)
    return result


def detect_video_provider(url: str) -> tuple[str, str] | None:
    """
    @brief Detect if URL is a known video provider and extract provider_id.

    @param url The URL to check.
    @return (provider_type, provider_id) or None if not a video URL.
    """
    for provider_name, pattern in VIDEO_PROVIDERS.items():
        match = pattern.search(url)
        if match:
            return (provider_name, match.group(1))
    return None


def _is_private_or_reserved(ip_str: str) -> bool:
    """Check if IP is private, loopback, or reserved."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_reserved
    except ValueError:
        return True


def is_safe_url(url: str) -> bool:
    """
    @brief SSRF protection: resolve DNS, reject private/loopback/reserved IPs.

    @param url The URL to validate.
    @return True if URL resolves to a public IP, False otherwise.
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False

        # Skip DNS for localhost-like hostnames
        if hostname.lower() in ("localhost", "127.0.0.1", "::1"):
            return False

        addrinfos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for info in addrinfos:
            # info is (family, type, proto, canonname, sockaddr)
            sockaddr = info[4]
            raw = sockaddr[0] if isinstance(sockaddr, (list, tuple)) else sockaddr
            ip_str = str(raw)
            if _is_private_or_reserved(ip_str):
                return False
        return True
    except (OSError, socket.gaierror, ValueError):
        return False


async def scrape_og_metadata(url: str) -> dict[str, str | None]:
    """
    @brief Fetch URL via httpx (5s timeout, 1MB limit), parse og:* meta tags.

    @param url The URL to fetch.
    @return Dict with title, description, image_url, site_name (None on error).
    """
    result: dict[str, str | None] = {
        "title": None,
        "description": None,
        "image_url": None,
        "site_name": None,
    }
    try:
        async with httpx.AsyncClient(
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "NexaraLinkPreview/1.0"},
            )
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return result

            # Limit body size
            content = response.text
            if len(content.encode("utf-8")) > HTTP_MAX_BYTES:
                return result

            # Parse og: meta tags with a simple regex (avoid heavy deps)
            og_pattern = re.compile(
                r'<meta\s+property="og:(\w+)"\s+content="([^"]*)"',
                re.IGNORECASE,
            )
            for match in og_pattern.finditer(content):
                key = match.group(1).lower()
                value = match.group(2).strip()
                if key == "title":
                    result["title"] = value or None
                elif key == "description":
                    result["description"] = value or None
                elif key == "image":
                    result["image_url"] = value or None
                elif key == "site_name":
                    result["site_name"] = value or None

            return result
    except Exception:
        return result


async def process_urls_for_post(
    post_id: uuid.UUID,
    text: str,
    repo: LinkPreviewRepository,
) -> None:
    """
    @brief Extract URLs from text, scrape each, store in DB.

    Skips URLs that fail SSRF check. Creates LinkPreview and PostLinkPreview
    junction rows. Called from PostService or Celery tasks.

    @param post_id Post UUID.
    @param text Post content to scan for URLs.
    @param repo LinkPreviewRepository instance.
    """
    from datetime import UTC, datetime, timedelta

    urls = extract_urls(text)
    for position, url in enumerate(urls):
        if not is_safe_url(url):
            continue

        metadata = await scrape_og_metadata(url)
        video = detect_video_provider(url)
        provider_type, provider_id = video if video else (None, None)

        url_hash = hashlib.sha256(url.encode()).hexdigest()
        defaults = {
            "title": metadata.get("title") or "",
            "description": metadata.get("description"),
            "image_url": metadata.get("image_url"),
            "site_name": metadata.get("site_name"),
            "provider_type": provider_type,
            "provider_id": provider_id,
            "fetch_error": not metadata.get("title") and not metadata.get("description"),
            "expires_at": datetime.now(UTC) + timedelta(days=90),
        }
        preview, _ = await repo.find_or_create(url, url_hash, defaults)
        await repo.create_post_link(post_id, preview.id, position)
