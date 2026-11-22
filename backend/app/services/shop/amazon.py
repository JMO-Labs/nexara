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
from dataclasses import dataclass
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

# ponytail: per-process token cache (by client id); Amazon suggests sharing
# it across processes (Valkey) once several workers hit the 1 TPS limit.
_tokens: dict[str, tuple[str, float]] = {}


@dataclass(frozen=True)
class Creds:
    """@brief Creators API credentials for one community."""

    client_id: str = ""
    client_secret: str = ""
    partner_tag: str = ""
    marketplace: str = "www.amazon.com"
    token_url: str = "https://api.amazon.com/auth/o2/token"


def creds_from(s: Settings, saved: dict[str, str | None] | None = None) -> Creds:
    """
    @brief Admin-saved credentials when complete, else the server environment.
    @param saved client_id, client_secret (plain), partner_tag, marketplace
    """
    saved = saved or {}
    if saved.get("client_id") and saved.get("client_secret") and saved.get("partner_tag"):
        return Creds(
            str(saved["client_id"]),
            str(saved["client_secret"]),
            str(saved["partner_tag"]),
            saved.get("marketplace") or s.AMAZON_MARKETPLACE,
            s.AMAZON_TOKEN_URL,
        )
    return Creds(
        s.AMAZON_CREATORS_CLIENT_ID,
        s.AMAZON_CREATORS_CLIENT_SECRET,
        s.AMAZON_PARTNER_TAG,
        s.AMAZON_MARKETPLACE,
        s.AMAZON_TOKEN_URL,
    )


def asin_from_url(url: str) -> str | None:
    """@brief ASIN from an Amazon product URL, or None (also None for non-Amazon hosts)."""
    host = (urlparse(url).hostname or "").lower()
    if not _AMAZON_HOST.search(host):
        return None
    m = _ASIN.search(urlparse(url).path + "/")
    return m.group(1).upper() if m else None


def configured(c: Creds) -> bool:
    """@brief Creators API credentials and partner tag are set."""
    return bool(c.client_id and c.client_secret and c.partner_tag)


async def access_token(client: httpx.AsyncClient, c: Creds) -> str:
    """@brief OAuth client-credentials token, cached until a minute before expiry."""
    cached = _tokens.get(c.client_id)
    if cached and cached[1] > time.monotonic() + 60:
        return cached[0]
    r = await client.post(
        c.token_url,
        json={
            "grant_type": "client_credentials",
            "client_id": c.client_id,
            "client_secret": c.client_secret,
            "scope": "creatorsapi::default",
        },
    )
    r.raise_for_status()
    body = r.json()
    token = str(body["access_token"])
    _tokens[c.client_id] = (token, time.monotonic() + int(body.get("expires_in", 3600)))
    return token


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


async def lookup(asins: list[str], c: Creds) -> dict[str, Product]:
    """
    @brief Look up to 10 ASINs in one call (one API transaction).
    @return products by ASIN; empty when not configured or on any error
    """
    if not asins or not configured(c):
        return {}
    try:
        async with httpx.AsyncClient(timeout=8.0, trust_env=False) as client:
            token = await access_token(client, c)
            r = await client.post(
                API_URL,
                headers={"Authorization": f"Bearer {token}", "x-marketplace": c.marketplace},
                json={
                    "itemIds": asins[:10],
                    "itemIdType": "ASIN",
                    "marketplace": c.marketplace,
                    "partnerTag": c.partner_tag,
                    "resources": RESOURCES,
                },
            )
            if r.status_code == 401:
                _tokens.pop(c.client_id, None)
            r.raise_for_status()
            return parse_items(r.json())
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("amazon_lookup_failed", error=type(exc).__name__, count=len(asins))
        return {}
