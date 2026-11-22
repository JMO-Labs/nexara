"""
@file shop_tasks.py
@brief Celery: fetch shop data for a new wishlist link, and the hourly
       refresh of prices (Amazon hourly, other shops daily).
"""

from __future__ import annotations

import asyncio
import uuid

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.repositories.link_preview_repo import LinkPreviewRepository
from app.repositories.wishlist_item_repo import WishlistItemRepository
from app.services.shop.refresh import ShopRefreshService
from app.tasks.celery_app import celery_app


async def _run(ids: list[uuid.UUID] | None) -> int:
    async with async_session_factory() as session:
        svc = ShopRefreshService(
            WishlistItemRepository(session), LinkPreviewRepository(session), get_settings()
        )
        n = await svc.refresh(ids)
        await session.commit()
        return n


@celery_app.task(name="app.tasks.shop_tasks.fetch_shop_item", queue="default")
def fetch_shop_item(item_id: str) -> int:
    """@brief Look up one wishlist link right after it is added or changed."""
    return asyncio.run(_run([uuid.UUID(item_id)]))


@celery_app.task(name="app.tasks.shop_tasks.refresh_shop_prices", queue="maintenance")
def refresh_shop_prices() -> int:
    """@brief Beat: refresh the stalest due wishlist links (50 per run)."""
    return asyncio.run(_run(None))
