"""
@file expense.py
@brief Request/response schemas for shared expense ledgers. Money in cents.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

CURRENCIES = (
    "USD EUR GBP CAD AUD NZD CHF SEK NOK DKK JPY CNY INR MXN BRL ZAR SGD HKD KRW PLN CZK HUF "
    "ILS TRY AED THB PHP IDR MYR CLP COP ARS"
).split()
"""@brief Currencies offered in settings and ledgers (ISO 4217)."""


class LedgerIn(BaseModel):
    """@brief Create a ledger; the creator is always a member."""

    name: str = Field(min_length=1, max_length=80)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    event_id: uuid.UUID | None = None
    wishlist_id: uuid.UUID | None = None
    member_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)


class LedgerUpdate(BaseModel):
    """@brief Rename or archive/unarchive a ledger."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    archived: bool | None = None


class MembersIn(BaseModel):
    """@brief Members to add."""

    user_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)


class ShareIn(BaseModel):
    """@brief One member's custom share."""

    user_id: uuid.UUID
    amount_cents: int = Field(ge=0, le=1_000_000_000)


class ExpenseIn(BaseModel):
    """@brief Add an expense. ``equal`` splits among ``split_among`` (default all)."""

    payer_id: uuid.UUID
    amount_cents: int = Field(gt=0, le=1_000_000_000)
    description: str = Field(min_length=1, max_length=200)
    spent_on: date
    split: Literal["equal", "custom"] = "equal"
    split_among: list[uuid.UUID] | None = None
    shares: list[ShareIn] | None = None


class SettleIn(BaseModel):
    """@brief Record that ``from_user_id`` paid ``to_user_id``."""

    from_user_id: uuid.UUID
    to_user_id: uuid.UUID
    amount_cents: int = Field(gt=0, le=1_000_000_000)


class CurrencyIn(BaseModel):
    """@brief Admin: community default currency."""

    currency: str = Field(pattern=r"^[A-Z]{3}$")


class CurrencyOut(BaseModel):
    """@brief Community default currency."""

    currency: str


class MemberOut(BaseModel):
    """@brief A ledger member; the name is masked when blocked."""

    user_id: uuid.UUID
    name: str


class ShareOut(BaseModel):
    """@brief One share of an expense."""

    user_id: uuid.UUID
    name: str
    amount_cents: int


class ExpenseOut(BaseModel):
    """@brief An expense with its shares."""

    id: uuid.UUID
    payer_id: uuid.UUID
    payer_name: str
    amount_cents: int
    description: str
    spent_on: date
    created_at: datetime
    shares: list[ShareOut]


class BalanceOut(BaseModel):
    """@brief Net balance; positive = owed money."""

    user_id: uuid.UUID
    name: str
    cents: int


class TransferOut(BaseModel):
    """@brief A suggested payment that clears the ledger."""

    from_user_id: uuid.UUID
    from_name: str
    to_user_id: uuid.UUID
    to_name: str
    cents: int


class LedgerSummary(BaseModel):
    """@brief Ledger row in lists."""

    id: uuid.UUID
    name: str
    currency: str
    event_id: uuid.UUID | None
    wishlist_id: uuid.UUID | None
    member_count: int
    archived: bool
    created_at: datetime


class LedgerOut(LedgerSummary):
    """@brief Full ledger: members, balances, suggested transfers and expenses."""

    created_by: uuid.UUID
    can_manage: bool
    members: list[MemberOut]
    balances: list[BalanceOut]
    transfers: list[TransferOut]
    expenses: list[ExpenseOut]
