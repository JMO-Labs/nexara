"""
@file lookup.py
@brief One entry point for shop facts behind a wishlist link: Amazon via
       the Creators API when configured, any other shop via its published
       product data (fetched with the SSRF-safe client).
"""

from __future__ import annotations

from urllib.parse import urljoin

from app.services.safe_fetch import safe_get
from app.services.shop import amazon
from app.services.shop.product import Product, extract_product

PAGE_MAX_BYTES = 2 * 1_048_576  # product pages are heavier than articles


async def lookup_product(url: str, creds: amazon.Creds) -> Product | None:
    """
    @brief Title, image and price for a shop link, or None when unknown.
    @param url product page URL (user supplied; fetched safely)
    @param creds Amazon Creators API credentials
    """
    asin = amazon.asin_from_url(url)
    if asin:
        # Amazon blocks ordinary fetchers; only the official API is used.
        return (await amazon.lookup([asin], creds)).get(asin)
    page = await safe_get(
        url,
        max_bytes=PAGE_MAX_BYTES,
        accept=lambda ct: ct in ("text/html", "application/xhtml+xml"),
    )
    if page is None:
        return None
    p = extract_product(page.body.decode("utf-8", errors="replace"))
    if p.image_url:
        p.image_url = urljoin(page.url, p.image_url)
    return p
