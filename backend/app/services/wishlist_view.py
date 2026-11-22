"""
@file wishlist_view.py
@brief Who may do what on a wishlist, and how its items look to a viewer.
       Pure helpers shared by the wishlist services.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.models.wishlist import Wishlist, WishlistClaim, WishlistItem
from app.schemas.wishlist import Claimer, ItemOut, Preview
from app.services.shop import amazon


@dataclass(frozen=True)
class Access:
    """@brief A viewer's rights on one list."""

    is_owner: bool
    is_recipient: bool

    @property
    def can_edit_items(self) -> bool:
        """@brief Owner and member recipients add and edit wishes."""
        return self.is_owner or self.is_recipient

    def sees_claims(self, w: Wishlist) -> bool:
        """@brief Claims are hidden from owner and recipients on surprise lists."""
        return not (w.hide_claims and self.can_edit_items)


def claim_value(item: WishlistItem, qty: int, amount_cents: int | None) -> int:
    """@brief Money a claim represents (gift price x qty, or fund pledge)."""
    if item.kind == "fund":
        return amount_cents or 0
    return (item.price_cents or 0) * qty


def build_items(
    items: list[WishlistItem],
    claims: list[tuple[WishlistClaim, str]],
    previews: dict[uuid.UUID, Any],
    viewer_id: uuid.UUID,
    sees_claims: bool,
    amazon_tag: str = "",
) -> tuple[list[ItemOut], int]:
    """
    @brief Items as the viewer sees them, plus the viewer's own claimed total.
    @return (items, my_total_cents)
    """
    by_item: dict[uuid.UUID, list[tuple[WishlistClaim, str]]] = {}
    for c, name in claims:
        by_item.setdefault(c.item_id, []).append((c, name))
    out: list[ItemOut] = []
    mine_total = 0
    for i in items:
        cs = by_item.get(i.id, [])
        fund = i.kind == "fund"
        total = sum((c.amount_cents or 0) if fund else c.qty for c, _ in cs)
        mine = next(
            ((c.amount_cents or 0) if fund else c.qty for c, _ in cs if c.user_id == viewer_id), 0
        )
        for c, _ in cs:
            if c.user_id == viewer_id:
                mine_total += claim_value(i, c.qty, c.amount_cents)
        p = previews.get(i.preview_id) if i.preview_id else None
        out.append(
            ItemOut(
                id=i.id,
                kind=i.kind,
                name=i.name,
                url=i.url,
                price_cents=i.price_cents,
                goal_cents=i.goal_cents,
                notes=i.notes,
                qty=i.qty,
                price_auto=i.price_auto,
                claimed=total if sees_claims else None,
                mine=mine if sees_claims else None,
                claimers=[
                    Claimer(user_id=c.user_id, name=n, qty=c.qty, amount_cents=c.amount_cents)
                    for c, n in cs
                ]
                if sees_claims
                else None,
                preview=Preview(
                    id=p.id,
                    title=p.title or None,
                    site_name=p.site_name,
                    has_image=bool(p.image_url),
                    price_cents=p.price_cents,
                    currency=p.currency,
                    buy_url=p.buy_url,
                    checked_at=p.fetched_at,
                )
                if p is not None and not p.fetch_error
                else None,
                link=(p.buy_url if p is not None else None)
                or (amazon.tagged_url(i.url, amazon_tag) if i.url else None)
                or i.url,
            )
        )
    return out, mine_total


def planned_cents(items: list[WishlistItem]) -> int:
    """@brief What the list adds up to: gifts at price x qty plus fund goals."""
    return sum(
        (i.goal_cents or 0) if i.kind == "fund" else (i.price_cents or 0) * i.qty for i in items
    )
