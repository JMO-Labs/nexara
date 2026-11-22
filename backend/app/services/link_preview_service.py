"""
@file link_preview_service.py
@brief OG link preview scraping; all fetching goes through safe_fetch (SSRF-safe).
"""

from __future__ import annotations

import hashlib
import html
import re
import uuid

from app.repositories.link_preview_repo import LinkPreviewRepository
from app.services.safe_fetch import UnsafeURLError, check_url, is_public_ip, resolve, safe_get

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

IMAGE_MAX_BYTES = 5 * 1_048_576
"""@brief Maximum proxied image size (5MB)."""


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


def is_safe_url(url: str) -> bool:
    """
    @brief Cheap pre-check: http(s) on 80/443 and every resolved address public.

    The fetch itself re-checks at connect time and on every redirect
    (see safe_fetch), so this only avoids queueing obviously bad URLs.

    @param url The URL to validate.
    @return True if the URL may be fetched.
    """
    try:
        host = check_url(url)
        addrs = resolve(host)
    except (UnsafeURLError, OSError, UnicodeError, ValueError):
        return False
    return bool(addrs) and all(is_public_ip(a) for a in addrs)


_OG = re.compile(r'<meta\s+property="og:(\w+)"\s+content="([^"]*)"', re.IGNORECASE)


async def scrape_og_metadata(url: str) -> dict[str, str | None]:
    """
    @brief Fetch an HTML page safely (5s, 1MB, SSRF-checked) and parse og:* tags.

    @param url The URL to fetch.
    @return Dict with title, description, image_url, site_name (None on error).
    """
    result: dict[str, str | None] = {
        "title": None,
        "description": None,
        "image_url": None,
        "site_name": None,
    }
    page = await safe_get(
        url,
        max_bytes=HTTP_MAX_BYTES,
        accept=lambda ct: ct in ("text/html", "application/xhtml+xml"),
    )
    if page is None:
        return result
    text = page.body.decode("utf-8", errors="replace")
    keys = {"title": "title", "description": "description", "image": "image_url"}
    keys["site_name"] = "site_name"
    for match in _OG.finditer(text):
        key = keys.get(match.group(1).lower())
        if key:
            result[key] = html.unescape(match.group(2).strip()) or None
    return result


async def fetch_image(url: str) -> tuple[bytes, str] | None:
    """
    @brief Fetch a preview image for the proxy (SSRF-checked, 5s, 5MB cap).

    SVG is refused (it can carry script). Redirects are re-checked per hop.

    @param url Remote image URL.
    @return (body, content_type) or None if unsafe, non-image, oversize, or failed.
    """
    img = await safe_get(
        url,
        max_bytes=IMAGE_MAX_BYTES,
        accept=lambda ct: ct.startswith("image/") and ct != "image/svg+xml",
    )
    return (img.body, img.content_type) if img else None


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
