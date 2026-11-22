"""
@file expenses.py
@brief Shared expense endpoints under /expenses (members-only ledgers).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, get_dispatcher, require_role
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.expense_repo import ExpenseRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.expense import (
    CurrencyIn,
    CurrencyOut,
    ExpenseIn,
    LedgerIn,
    LedgerOut,
    LedgerSummary,
    LedgerUpdate,
    MembersIn,
    SettleIn,
)
from app.services.expense_service import ExpenseService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/expenses", tags=["expenses"])


def _build_service(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> ExpenseService:
    """@brief Build ExpenseService with injected dependencies."""
    cid = uuid.UUID(settings.COMMUNITY_ID)
    notif = NotificationService(
        NotificationRepository(db), SettingsRepository(db), cid, dispatcher=get_dispatcher()
    )
    return ExpenseService(ExpenseRepository(db), CommunityRepository(db), notif, cid)


@router.get("/currency", response_model=CurrencyOut)
async def get_currency(
    _user: User = Depends(get_current_user),
    service: ExpenseService = Depends(_build_service),
) -> Any:
    """@brief The community default currency."""
    return CurrencyOut(currency=await service.get_currency())


@router.put("/currency", response_model=CurrencyOut)
async def set_currency(
    body: CurrencyIn,
    _admin: User = Depends(require_role("admin")),
    service: ExpenseService = Depends(_build_service),
) -> Any:
    """@brief Admin: change the community default currency."""
    return CurrencyOut(currency=await service.set_currency(body.currency))


@router.post("/ledgers", status_code=201, response_model=LedgerOut)
async def create_ledger(
    body: LedgerIn,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(_build_service),
) -> Any:
    """@brief Create a ledger."""
    return await service.create_ledger(user, body)


@router.get("/ledgers", response_model=list[LedgerSummary])
async def list_ledgers(
    event_id: uuid.UUID | None = None,
    wishlist_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(_build_service),
) -> Any:
    """@brief My ledgers, optionally for one event or wishlist."""
    return await service.list_ledgers(user, event_id, wishlist_id)


@router.post("/ledgers/from-wishlist-item/{item_id}", response_model=LedgerOut)
async def split_gift(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(_build_service),
) -> Any:
    """@brief "Split this gift": reuse or create the ledger tied to the item's wishlist."""
    return await service.from_wishlist_item(item_id, user)


@router.get("/ledgers/{ledger_id}", response_model=LedgerOut)
async def get_ledger(
    ledger_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(_build_service),
) -> Any:
    """@brief One ledger with balances (404 for non-members)."""
    return await service.get_ledger(ledger_id, user)


@router.patch("/ledgers/{ledger_id}", response_model=LedgerOut)
async def update_ledger(
    ledger_id: uuid.UUID,
    body: LedgerUpdate,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(_build_service),
) -> Any:
    """@brief Rename or archive."""
    return await service.update_ledger(ledger_id, user, body)


@router.post("/ledgers/{ledger_id}/members", response_model=LedgerOut)
async def add_members(
    ledger_id: uuid.UUID,
    body: MembersIn,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(_build_service),
) -> Any:
    """@brief Add members."""
    return await service.add_members(ledger_id, user, body.user_ids)


@router.delete("/ledgers/{ledger_id}/members/{user_id}", status_code=204)
async def remove_member(
    ledger_id: uuid.UUID,
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(_build_service),
) -> Response:
    """@brief Remove a member (or leave)."""
    await service.remove_member(ledger_id, user, user_id)
    return Response(status_code=204)


@router.post("/ledgers/{ledger_id}/expenses", status_code=201, response_model=LedgerOut)
async def add_expense(
    ledger_id: uuid.UUID,
    body: ExpenseIn,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(_build_service),
) -> Any:
    """@brief Add an expense; returns the updated ledger."""
    return await service.add_expense(ledger_id, user, body)


@router.delete("/ledgers/{ledger_id}/expenses/{expense_id}", response_model=LedgerOut)
async def delete_expense(
    ledger_id: uuid.UUID,
    expense_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(_build_service),
) -> Any:
    """@brief Delete an expense; returns the updated ledger."""
    return await service.delete_expense(ledger_id, expense_id, user)


@router.post("/ledgers/{ledger_id}/settle", response_model=LedgerOut)
async def settle(
    ledger_id: uuid.UUID,
    body: SettleIn,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(_build_service),
) -> Any:
    """@brief Record a payment between two members."""
    return await service.settle(ledger_id, user, body)
