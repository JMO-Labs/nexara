"""
@file refresh.py
@brief Keep wishlist shop data fresh: look up linked items (Amazon in
       batches of 10 via the Creators API, other shops one by one), store
       the product facts on the link preview, and update prices that follow
       the shop (``price_auto``) when the currency matches the list.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog

from app.core.config import Settings
from app.models.wishlist import WishlistItem
from app.repositories.link_preview_repo import LinkPreviewRepository
from app.repositories.wishlist_item_repo import WishlistItemRepository
from app.services.shop import amazon
from app.services.shop.lookup import lookup_product
from app.services.shop.product import Product

logger = structlog.get_logger(__name__)

AMAZON_TTL = timedelta(hours=1)  # Creators API: offers may be cached 1 hour
OTHER_TTL = timedelta(days=1)


def apply_price(item: WishlistItem, product: Product, list_currency: str) -> bool:
    """
    @brief Follow the shop price unless someone typed their own.
    @return True when the item's price changed
    """
    if item.kind != "gift" or product.price_cents is None:
        return False
    if (product.currency or list_currency) != list_currency:
        return False  # never convert currencies silently
    if item.price_cents is not None and not item.price_auto:
        return False
    changed = item.price_cents != product.price_cents
    item.price_cents, item.price_auto = product.price_cents, True
    return changed


class ShopRefreshService:
    """@brief Look up and store shop facts for wishlist links."""

    def __init__(
        self, items: WishlistItemRepository, previews: LinkPreviewRepository, settings: Settings
    ) -> None:
        self._items = items
        self._previews = previews
        self._settings = settings

    async def refresh(self, ids: list[uuid.UUID] | None = None, limit: int = 50) -> int:
        """
        @brief Refresh given items, or the stalest due ones.
        @return number of items that got shop data
        """
        now = datetime.now(UTC)
        rows = await self._items.linked_for_refresh(
            ids=ids, amazon_before=now - AMAZON_TTL, other_before=now - OTHER_TTL, limit=limit
        )
        asins = {i.id: amazon.asin_from_url(i.url or "") for i, _c in rows}
        found: dict[str, Product] = {}
        wanted = sorted({a for a in asins.values() if a})
        for k in range(0, len(wanted), 10):
            found |= await amazon.lookup(wanted[k : k + 10], self._settings)
        done = 0
        for item, currency in rows:
            asin = asins[item.id]
            try:
                product = (
                    found.get(asin)
                    if asin
                    else await lookup_product(item.url or "", self._settings)
                )
            except Exception:  # one bad shop must not sink the batch
                logger.warning("shop_lookup_failed", item_id=str(item.id), exc_info=True)
                product = None
            if product is None:
                # Stamp fetched_at so a failing link waits its TTL instead of
                # staying first in the queue; keep any good data it had.
                failed = {} if item.preview_id else {"title": "", "fetch_error": True}
                item.preview_id = (await self._previews.upsert_shop(item.url or "", failed)).id
                continue
            preview = await self._previews.upsert_shop(
                item.url or "",
                {
                    "title": product.title or "",
                    "image_url": product.image_url,
                    "site_name": product.site_name,
                    "price_cents": product.price_cents,
                    "currency": product.currency,
                    "buy_url": product.buy_url,
                    "fetch_error": not (product.title or product.image_url or product.price_cents),
                },
            )
            item.preview_id = preview.id
            apply_price(item, product, currency)
            done += 1
        logger.info("shop_refresh", checked=len(rows), updated=done)
        return done
