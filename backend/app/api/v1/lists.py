"""
@file lists.py
@brief Lists API: list CRUD, items, completion, members and signups.

Domain errors (NotFoundError, AuthorizationError, ...) are rendered as the
standard ``{"error": {"code", "message"}}`` envelope by the global handlers.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.list_dependencies import (
    get_community_id,
    get_list_completion_service,
    get_list_item_service,
    get_list_service,
    get_list_signup_service,
)
from app.models.user import User
from app.schemas.list import (
    ListCreate,
    ListItemCreate,
    ListItemOut,
    ListItemPage,
    ListItemUpdate,
    ListMemberAdd,
    ListMemberOut,
    ListOut,
    ListPage,
    ListUpdate,
    Pagination,
    SignupClaim,
    SignupOut,
)
from app.services.list_completion_service import ListCompletionService
from app.services.list_items_service import ListItemService
from app.services.list_service import ListService
from app.services.list_signup_service import ListSignupService

router = APIRouter(prefix="/lists", tags=["lists"])


def _is_admin(user: User) -> bool:
    return user.role in ("admin", "owner")


def _page(next_cursor: str | None) -> Pagination:
    return Pagination(cursor=next_cursor, has_more=next_cursor is not None)


async def _guard_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    user: User,
    community_id: uuid.UUID,
    items: ListItemService,
    lists: ListService | None = None,
) -> None:
    """@brief 404 unless the item is in ``list_id`` (and the list is visible when ``lists``)."""
    if lists is not None:
        await lists.get_by_id(list_id, user.id)
    await items.ensure_in_list(community_id, list_id, item_id)


# ── Lists ─────────────────────────────────────────────────────────


@router.get("", response_model=ListPage)
async def list_lists(
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: ListService = Depends(get_list_service),
) -> ListPage:
    """@brief Keyset page of lists visible to the caller."""
    rows, nxt = await service.list_visible(user.id, cursor, limit)
    return ListPage(lists=[ListOut.model_validate(r) for r in rows], pagination=_page(nxt))


@router.post("", response_model=ListOut, status_code=201)
async def create_list(
    body: ListCreate,
    user: User = Depends(get_current_user),
    service: ListService = Depends(get_list_service),
) -> ListOut:
    """@brief Create a list owned by the caller."""
    lst = await service.create(user.id, **body.model_dump(exclude={"color"}))
    return ListOut.model_validate(lst)


@router.get("/{list_id}", response_model=ListOut)
async def get_list(
    list_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ListService = Depends(get_list_service),
) -> ListOut:
    """@brief Fetch a visible list (404 when missing or hidden)."""
    return ListOut.model_validate(await service.get_by_id(list_id, user.id))


@router.put("/{list_id}", response_model=ListOut)
async def update_list(
    list_id: uuid.UUID,
    body: ListUpdate,
    user: User = Depends(get_current_user),
    service: ListService = Depends(get_list_service),
) -> ListOut:
    """@brief Update a list (owner/admin; 403 otherwise)."""
    data = body.model_dump(exclude_unset=True)
    return ListOut.model_validate(await service.update(list_id, user.id, data, _is_admin(user)))


@router.delete("/{list_id}", status_code=204)
async def delete_list(
    list_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ListService = Depends(get_list_service),
) -> Response:
    """@brief Soft-delete a list (owner only)."""
    await service.delete(list_id, user.id, _is_admin(user))
    return Response(status_code=204)


# ── Items ─────────────────────────────────────────────────────────


@router.get("/{list_id}/items", response_model=ListItemPage)
async def list_items(
    list_id: uuid.UUID,
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = "position",
    user: User = Depends(get_current_user),
    community_id: uuid.UUID = Depends(get_community_id),
    service: ListItemService = Depends(get_list_item_service),
) -> ListItemPage:
    """@brief Keyset page of a list's items."""
    rows, nxt = await service.list_items(community_id, list_id, user.id, cursor, limit, sort_by)
    return ListItemPage(items=[ListItemOut.model_validate(r) for r in rows], pagination=_page(nxt))


@router.post("/{list_id}/items", response_model=ListItemOut, status_code=201)
async def create_item(
    list_id: uuid.UUID,
    body: ListItemCreate,
    user: User = Depends(get_current_user),
    community_id: uuid.UUID = Depends(get_community_id),
    service: ListItemService = Depends(get_list_item_service),
) -> ListItemOut:
    """@brief Add an item to a list (owner only)."""
    item = await service.create(community_id, list_id, user.id, body.values, body.position)
    return ListItemOut.model_validate(item)


@router.put("/{list_id}/items/{item_id}", response_model=ListItemOut)
async def update_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ListItemUpdate,
    user: User = Depends(get_current_user),
    community_id: uuid.UUID = Depends(get_community_id),
    service: ListItemService = Depends(get_list_item_service),
) -> ListItemOut:
    """@brief Update an item's values (owner only)."""
    await service.ensure_in_list(community_id, list_id, item_id)
    item = await service.update(community_id, item_id, user.id, body.values)
    return ListItemOut.model_validate(item)


@router.delete("/{list_id}/items/{item_id}", status_code=204)
async def delete_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    community_id: uuid.UUID = Depends(get_community_id),
    service: ListItemService = Depends(get_list_item_service),
) -> Response:
    """@brief Soft-delete an item (owner only)."""
    await service.ensure_in_list(community_id, list_id, item_id)
    await service.delete(community_id, item_id, user.id)
    return Response(status_code=204)


@router.post("/{list_id}/items/{item_id}/complete", response_model=ListItemOut)
async def complete_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    field_key: str | None = None,
    user: User = Depends(get_current_user),
    service: ListCompletionService = Depends(get_list_completion_service),
    community_id: uuid.UUID = Depends(get_community_id),
    items: ListItemService = Depends(get_list_item_service),
) -> ListItemOut:
    """@brief Mark an item complete."""
    await _guard_item(list_id, item_id, user, community_id, items)
    return ListItemOut.model_validate(await service.complete_item(item_id, user.id, field_key))


@router.post("/{list_id}/items/{item_id}/uncomplete", response_model=ListItemOut)
async def uncomplete_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    field_key: str | None = None,
    user: User = Depends(get_current_user),
    service: ListCompletionService = Depends(get_list_completion_service),
    community_id: uuid.UUID = Depends(get_community_id),
    items: ListItemService = Depends(get_list_item_service),
) -> ListItemOut:
    """@brief Reverse a completion."""
    await _guard_item(list_id, item_id, user, community_id, items)
    return ListItemOut.model_validate(await service.uncomplete_item(item_id, user.id, field_key))


# ── Members ───────────────────────────────────────────────────────


@router.get("/{list_id}/members", response_model=list[ListMemberOut])
async def list_members(
    list_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ListService = Depends(get_list_service),
) -> list[ListMemberOut]:
    """@brief Members of a visible list (404 when missing or hidden)."""
    rows = await service.list_members(list_id, user.id)
    return [ListMemberOut.model_validate(m) for m in rows]


@router.post("/{list_id}/members", response_model=ListMemberOut, status_code=201)
async def add_member(
    list_id: uuid.UUID,
    body: ListMemberAdd,
    user: User = Depends(get_current_user),
    service: ListService = Depends(get_list_service),
) -> ListMemberOut:
    """@brief Add a member to a members-visibility list."""
    member = await service.add_member(list_id, user.id, body.user_id, body.role, _is_admin(user))
    return ListMemberOut.model_validate(member)


@router.delete("/{list_id}/members/{member_id}", status_code=204)
async def remove_member(
    list_id: uuid.UUID,
    member_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ListService = Depends(get_list_service),
) -> Response:
    """@brief Remove a member from a list."""
    await service.remove_member(list_id, user.id, member_id, _is_admin(user))
    return Response(status_code=204)


# ── Signups ───────────────────────────────────────────────────────


@router.get("/{list_id}/items/{item_id}/signups", response_model=list[SignupOut])
async def list_signups(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ListSignupService = Depends(get_list_signup_service),
    community_id: uuid.UUID = Depends(get_community_id),
    items: ListItemService = Depends(get_list_item_service),
    lists: ListService = Depends(get_list_service),
) -> list[SignupOut]:
    """@brief Claims on an item."""
    await _guard_item(list_id, item_id, user, community_id, items, lists)
    return [SignupOut.model_validate(c) for c in await service.get_signups_for_item(item_id)]


@router.post("/{list_id}/items/{item_id}/signups", response_model=SignupOut, status_code=201)
async def claim_signup(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    body: SignupClaim,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: ListSignupService = Depends(get_list_signup_service),
    community_id: uuid.UUID = Depends(get_community_id),
    items: ListItemService = Depends(get_list_item_service),
    lists: ListService = Depends(get_list_service),
) -> SignupOut:
    """@brief Claim slots on an item."""
    await _guard_item(list_id, item_id, user, community_id, items, lists)
    claim = await service.claim_signup(item_id, user.id, body.quantity, db, body.note)
    return SignupOut.model_validate(claim)


@router.delete("/{list_id}/items/{item_id}/signups", status_code=204)
async def release_signup(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: ListSignupService = Depends(get_list_signup_service),
    community_id: uuid.UUID = Depends(get_community_id),
    items: ListItemService = Depends(get_list_item_service),
    lists: ListService = Depends(get_list_service),
) -> Response:
    """@brief Release the caller's claim on an item."""
    await _guard_item(list_id, item_id, user, community_id, items, lists)
    await service.release_signup(item_id, user.id, db)
    return Response(status_code=204)
