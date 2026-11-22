"""
@file amazon.py
@brief Amazon product data through the official Creators API (optional;
       enabled when AMAZON_CREATORS_* settings are present). Amazon serves a
       captcha to ordinary fetchers, so this is the only reliable route.

Calls go only to Amazon's fixed API hosts (never a user-supplied URL).
Prices are from Amazon's default in-marketplace shipping address and may
differ for a given shopper; links use Amazon's partner-tagged
``detailPageURL`` unchanged, as the API terms require.
"""

from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

from app.core.config import Settings
from app.services.shop.product import Product, to_cents

logger = structlog.get_logger(__name__)

API_URL = "https://creatorsapi.amazon/catalog/v1/getItems"
RESOURCES = [
    "itemInfo.title",
    "images.primary.large",
    "images.primary.medium",
    "offersV2.listings.price",
]
_ASIN = re.compile(
    r"/(?:dp|gp/product|gp/aw/d|exec/obidos/asin|o/ASIN)/([A-Z0-9]{10})(?:[/?]|$)", re.I
)
_AMAZON_HOST = re.compile(
    r"(^|\.)amazon\.(com|ca|com\.mx|com\.br|co\.uk|de|fr|it|es|nl|com\.be|in|ie|pl|se|com\.tr|ae|sa|eg|co\.jp|sg|com\.au)$"
)

# ponytail: per-process token cache; Amazon suggests sharing it across
# processes (Valkey) once several workers hit the 1 TPS limit.
_token: dict[str, Any] = {"value": None, "expires": 0.0}


def asin_from_url(url: str) -> str | None:
    """@brief ASIN from an Amazon product URL, or None (also None for non-Amazon hosts)."""
    host = (urlparse(url).hostname or "").lower()
    if not _AMAZON_HOST.search(host):
        return None
    m = _ASIN.search(urlparse(url).path + "/")
    return m.group(1).upper() if m else None


def configured(s: Settings) -> bool:
    """@brief Creators API credentials and partner tag are set."""
    return bool(
        s.AMAZON_CREATORS_CLIENT_ID and s.AMAZON_CREATORS_CLIENT_SECRET and s.AMAZON_PARTNER_TAG
    )


async def _access_token(client: httpx.AsyncClient, s: Settings) -> str:
    if _token["value"] and _token["expires"] > time.monotonic() + 60:
        return str(_token["value"])
    r = await client.post(
        s.AMAZON_TOKEN_URL,
        json={
            "grant_type": "client_credentials",
            "client_id": s.AMAZON_CREATORS_CLIENT_ID,
            "client_secret": s.AMAZON_CREATORS_CLIENT_SECRET,
            "scope": "creatorsapi::default",
        },
    )
    r.raise_for_status()
    body = r.json()
    _token.update(
        value=body["access_token"], expires=time.monotonic() + int(body.get("expires_in", 3600))
    )
    return str(body["access_token"])


def _dig(d: Any, *path: str) -> Any:
    for k in path:
        d = d.get(k) if isinstance(d, dict) else None
    return d


def parse_items(body: dict[str, Any]) -> dict[str, Product]:
    """
    @brief Products by ASIN from a getItems response.
    @details The docs spell the root both ``itemResults`` and ``itemsResult``;
             accept either. Prefer the large image, else medium/small.
    """
    root = body.get("itemResults") or body.get("itemsResult") or {}
    out: dict[str, Product] = {}
    for it in root.get("items") or []:
        asin = str(it.get("asin") or "").upper()
        if not asin:
            continue
        img = next(
            (
                u
                for size in ("large", "medium", "small")
                if (u := _dig(it, "images", "primary", size, "url"))
            ),
            None,
        )
        money: dict[str, Any] = {}
        for listing in _dig(it, "offersV2", "listings") or []:
            money = _dig(listing, "price", "money") or {}
            if money:
                break
        out[asin] = Product(
            title=_dig(it, "itemInfo", "title", "displayValue"),
            image_url=img,
            price_cents=to_cents(money.get("amount")),
            currency=(str(money["currency"]).upper() if money.get("currency") else None),
            site_name="Amazon",
            buy_url=it.get("detailPageURL"),
        )
    return out


async def lookup(asins: list[str], s: Settings) -> dict[str, Product]:
    """
    @brief Look up to 10 ASINs in one call (one API transaction).
    @return products by ASIN; empty when not configured or on any error
    """
    if not asins or not configured(s):
        return {}
    try:
        async with httpx.AsyncClient(timeout=8.0, trust_env=False) as client:
            token = await _access_token(client, s)
            r = await client.post(
                API_URL,
                headers={"Authorization": f"Bearer {token}", "x-marketplace": s.AMAZON_MARKETPLACE},
                json={
                    "itemIds": asins[:10],
                    "itemIdType": "ASIN",
                    "marketplace": s.AMAZON_MARKETPLACE,
                    "partnerTag": s.AMAZON_PARTNER_TAG,
                    "resources": RESOURCES,
                },
            )
            if r.status_code == 401:
                _token["value"] = None
            r.raise_for_status()
            return parse_items(r.json())
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("amazon_lookup_failed", error=type(exc).__name__, count=len(asins))
        return {}
