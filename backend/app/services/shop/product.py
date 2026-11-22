"""
@file product.py
@brief Pull title, image and price out of a shop's product page: schema.org
       Product JSON-LD first (what most shops publish), then Open Graph and
       ``product:price`` meta tags. Pure functions, no network.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

_LD = re.compile(
    r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
_META = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r"""([a-zA-Z:_-]+)\s*=\s*("([^"]*)"|'([^']*)')""")


@dataclass
class Product:
    """@brief What a shop page says about one product."""

    title: str | None = None
    image_url: str | None = None
    price_cents: int | None = None
    currency: str | None = None
    site_name: str | None = None
    buy_url: str | None = None


def to_cents(value: Any) -> int | None:
    """@brief "1,299.99" / 12.5 / "$8" -> cents; None when not a positive amount."""
    if value is None or isinstance(value, bool):
        return None
    text = re.sub(r"[^\d.]", "", str(value).replace(",", ""))
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None
    cents = int((amount * 100).to_integral_value())
    return cents if 0 < cents < 10_000_000_00 else None


def _meta(page: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for tag in _META.findall(page):
        attrs = {m.group(1).lower(): m.group(3) or m.group(4) or "" for m in _ATTR.finditer(tag)}
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").lower()
        if key and "content" in attrs and key not in out:
            out[key] = html.unescape(attrs["content"]).strip()
    return out


def _walk(node: Any) -> Any:
    """@brief Yield every dict in a JSON-LD document (lists and @graph included)."""
    if isinstance(node, list):
        for n in node:
            yield from _walk(n)
    elif isinstance(node, dict):
        yield node
        for v in node.values():
            if isinstance(v, (list, dict)):
                yield from _walk(v)


def _is_product(d: dict[str, Any]) -> bool:
    t = d.get("@type")
    types = t if isinstance(t, list) else [t]
    return any(str(x).lower() in ("product", "productgroup") for x in types)


def _first_image(img: Any) -> str | None:
    if isinstance(img, str):
        return img
    if isinstance(img, list) and img:
        return _first_image(img[0])
    if isinstance(img, dict):
        return img.get("url") or img.get("contentUrl")
    return None


def _offer_price(offers: Any) -> tuple[int | None, str | None]:
    for o in offers if isinstance(offers, list) else [offers]:
        if not isinstance(o, dict):
            continue
        spec = o.get("priceSpecification")
        spec = spec[0] if isinstance(spec, list) and spec else spec
        price = o.get("price") or o.get("lowPrice") or (spec or {}).get("price")
        cents = to_cents(price)
        if cents:
            cur = o.get("priceCurrency") or (spec or {}).get("priceCurrency")
            return cents, str(cur).upper()[:3] if cur else None
    return None, None


def extract_product(page: str) -> Product:
    """
    @brief Best-effort product facts from an HTML page.
    @param page HTML text
    @return Product (fields None when the page doesn't say)
    """
    p = Product()
    for block in _LD.findall(page):
        try:
            doc = json.loads(block.strip())
        except (ValueError, RecursionError):
            try:  # a few shops HTML-escape their JSON-LD
                doc = json.loads(html.unescape(block.strip()))
            except (ValueError, RecursionError):
                continue
        for d in _walk(doc):
            if not _is_product(d):
                continue
            p.title = p.title or (str(d["name"]) if d.get("name") else None)
            p.image_url = p.image_url or _first_image(d.get("image"))
            if p.price_cents is None:
                p.price_cents, p.currency = _offer_price(d.get("offers"))
    m = _meta(page)
    p.title = p.title or m.get("og:title") or m.get("twitter:title")
    p.image_url = p.image_url or m.get("og:image") or m.get("twitter:image")
    p.site_name = m.get("og:site_name")
    if p.price_cents is None:
        p.price_cents = to_cents(m.get("product:price:amount") or m.get("og:price:amount"))
        cur = m.get("product:price:currency") or m.get("og:price:currency")
        p.currency = cur.upper()[:3] if cur else None
    return p
