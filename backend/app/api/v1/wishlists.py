"""
@file wishlists.py
@brief Wishlists: browse, create and edit your own (or a household
       member's/pet's), add wishes, and claim gifts on other people's lists.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.wishlist_item_repo import WishlistItemRepository
from app.repositories.wishlist_repo import WishlistRepository
from app.schemas.common import MessageResponse
from app.schemas.wishlist import (
    ClaimIn,
    ItemIn,
    ItemUpdate,
    WishlistCreate,
    WishlistDetail,
    WishlistOut,
    WishlistUpdate,
)
from app.services.wishlist_gift_service import WishlistGiftService
from app.services.wishlist_service import WishlistService

router = APIRouter(prefix="/wishlists", tags=["wishlists"])


def _service(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> WishlistService:
    """@brief WishlistService bound to the request session."""
    return WishlistService(WishlistRepository(db), WishlistItemRepository(db), user.community_id)


def _gifts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    lists: WishlistService = Depends(_service),
) -> WishlistGiftService:
    """@brief WishlistGiftService bound to the request session."""
    return WishlistGiftService(lists, WishlistItemRepository(db), user.community_id)


@router.get("", response_model=list[WishlistOut])
async def list_wishlists(
    person_id: uuid.UUID | None = Query(None),
    household_id: uuid.UUID | None = Query(None),
    owner_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    svc: WishlistService = Depends(_service),
) -> list[WishlistOut]:
    """@brief Wishlists you can see; filter by person (by or for), household member or creator."""
    return await svc.list(user, person_id, household_id, owner_id)


@router.post("", response_model=WishlistDetail, status_code=201)
async def create_wishlist(
    body: WishlistCreate,
    user: User = Depends(get_current_user),
    svc: WishlistService = Depends(_service),
) -> WishlistDetail:
    """@brief Start a wishlist."""
    return await svc.create(body, user)


@router.get("/{wishlist_id}", response_model=WishlistDetail)
async def get_wishlist(
    wishlist_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: WishlistService = Depends(_service),
) -> WishlistDetail:
    """@brief A wishlist with its items."""
    return await svc.get(wishlist_id, user)


@router.patch("/{wishlist_id}", response_model=WishlistDetail)
async def update_wishlist(
    wishlist_id: uuid.UUID,
    body: WishlistUpdate,
    user: User = Depends(get_current_user),
    svc: WishlistService = Depends(_service),
) -> WishlistDetail:
    """@brief Edit a wishlist (owner)."""
    return await svc.update(wishlist_id, body, user)


@router.delete("/{wishlist_id}", response_model=MessageResponse)
async def delete_wishlist(
    wishlist_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: WishlistService = Depends(_service),
) -> MessageResponse:
    """@brief Delete a wishlist (owner)."""
    await svc.delete(wishlist_id, user)
    return MessageResponse(message="Wishlist deleted")


@router.post("/{wishlist_id}/items", response_model=WishlistDetail, status_code=201)
async def add_item(
    wishlist_id: uuid.UUID,
    body: ItemIn,
    user: User = Depends(get_current_user),
    svc: WishlistGiftService = Depends(_gifts),
) -> WishlistDetail:
    """@brief Add a gift or cash fund (creator or member recipients)."""
    return await svc.add_item(wishlist_id, body, user)


@router.patch("/{wishlist_id}/items/{item_id}", response_model=WishlistDetail)
async def update_item(
    wishlist_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ItemUpdate,
    user: User = Depends(get_current_user),
    svc: WishlistGiftService = Depends(_gifts),
) -> WishlistDetail:
    """@brief Edit a wish (creator or member recipients)."""
    return await svc.update_item(wishlist_id, item_id, body, user)


@router.delete("/{wishlist_id}/items/{item_id}", response_model=MessageResponse)
async def delete_item(
    wishlist_id: uuid.UUID,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: WishlistGiftService = Depends(_gifts),
) -> MessageResponse:
    """@brief Remove a wish (creator or member recipients)."""
    await svc.delete_item(wishlist_id, item_id, user)
    return MessageResponse(message="Item removed")


@router.put("/{wishlist_id}/items/{item_id}/claim", response_model=WishlistDetail)
async def claim_item(
    wishlist_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ClaimIn,
    user: User = Depends(get_current_user),
    svc: WishlistGiftService = Depends(_gifts),
) -> WishlistDetail:
    """@brief Claim a gift or pledge to a fund (hidden from the list's people on surprise lists)."""
    return await svc.claim(wishlist_id, item_id, body, user)


@router.delete("/{wishlist_id}/items/{item_id}/claim", response_model=WishlistDetail)
async def release_item(
    wishlist_id: uuid.UUID,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: WishlistGiftService = Depends(_gifts),
) -> WishlistDetail:
    """@brief Take back your claim."""
    return await svc.release(wishlist_id, item_id, user)
