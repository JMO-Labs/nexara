"""
@file expense_repo.py
@brief Data access for expense ledgers. Ledgers are visible to members only;
       callers check membership before reading anything else.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.expense import Expense, ExpenseLedger, ExpenseShare, LedgerMember, Settlement
from app.models.subgroup import SubgroupMember
from app.models.user import User
from app.models.wishlist import Wishlist, WishlistItem
from app.repositories.visibility_preds import not_blocked
from app.repositories.wishlist_repo import wishlist_visible


class ExpenseRepository:
    """@brief Async repository for the expense tables."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- ledgers -----------------------------------------------------------
    async def create_ledger(
        self, community_id: uuid.UUID, member_ids: list[uuid.UUID], **values: Any
    ) -> ExpenseLedger:
        """@brief Insert a ledger and its members."""
        row = ExpenseLedger(community_id=community_id, **values)
        self._session.add(row)
        await self._session.flush()
        for uid in member_ids:
            self._session.add(LedgerMember(ledger_id=row.id, user_id=uid))
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_ledger(
        self, ledger_id: uuid.UUID, community_id: uuid.UUID, *, lock: bool = False
    ) -> ExpenseLedger | None:
        """@brief Ledger by id; ``lock`` takes ``FOR UPDATE`` to serialize settles."""
        stmt = select(ExpenseLedger).where(
            ExpenseLedger.id == ledger_id, ExpenseLedger.community_id == community_id
        )
        if lock:
            stmt = stmt.with_for_update()
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def is_member(self, ledger_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief Whether the user belongs to the ledger."""
        stmt = select(LedgerMember.user_id).where(
            LedgerMember.ledger_id == ledger_id, LedgerMember.user_id == user_id
        )
        return (await self._session.execute(stmt)).first() is not None

    async def list_ledgers(
        self,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        *,
        event_id: uuid.UUID | None = None,
        wishlist_id: uuid.UUID | None = None,
    ) -> list[tuple[ExpenseLedger, int]]:
        """@brief The viewer's ledgers with member counts, newest first."""
        count = (
            select(func.count()).where(LedgerMember.ledger_id == ExpenseLedger.id).scalar_subquery()
        )
        mine = exists().where(
            LedgerMember.ledger_id == ExpenseLedger.id, LedgerMember.user_id == viewer_id
        )
        stmt = select(ExpenseLedger, count).where(ExpenseLedger.community_id == community_id, mine)
        if event_id is not None:
            stmt = stmt.where(ExpenseLedger.event_id == event_id)
        if wishlist_id is not None:
            stmt = stmt.where(ExpenseLedger.wishlist_id == wishlist_id)
        stmt = stmt.order_by(
            ExpenseLedger.archived_at.is_not(None), ExpenseLedger.created_at.desc()
        )
        return [(r, int(n)) for r, n in (await self._session.execute(stmt)).all()]

    async def member_count(self, ledger_id: uuid.UUID) -> int:
        """@brief Number of members."""
        stmt = select(func.count()).where(LedgerMember.ledger_id == ledger_id)
        return int((await self._session.execute(stmt)).scalar_one())

    async def member_ids(self, ledger_id: uuid.UUID) -> list[uuid.UUID]:
        """@brief Member ids ordered by id (stable split order)."""
        stmt = (
            select(LedgerMember.user_id)
            .where(LedgerMember.ledger_id == ledger_id)
            .order_by(LedgerMember.user_id)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def add_members(self, ledger_id: uuid.UUID, user_ids: list[uuid.UUID]) -> None:
        """@brief Add members, ignoring existing ones."""
        have = set(await self.member_ids(ledger_id))
        for uid in dict.fromkeys(user_ids):
            if uid not in have:
                self._session.add(LedgerMember(ledger_id=ledger_id, user_id=uid))
        await self._session.flush()

    async def remove_member(self, ledger_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """@brief Remove one member."""
        await self._session.execute(
            delete(LedgerMember).where(
                LedgerMember.ledger_id == ledger_id, LedgerMember.user_id == user_id
            )
        )

    async def has_activity(self, ledger_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief User paid, owes a share, or settled in this ledger."""
        paid = exists().where(
            Expense.ledger_id == ledger_id,
            Expense.deleted_at.is_(None),
            Expense.payer_id == user_id,
        )
        shared = exists().where(
            Expense.id == ExpenseShare.expense_id,
            Expense.ledger_id == ledger_id,
            Expense.deleted_at.is_(None),
            ExpenseShare.user_id == user_id,
        )
        settled = exists().where(
            Settlement.ledger_id == ledger_id,
            or_(Settlement.from_user_id == user_id, Settlement.to_user_id == user_id),
        )
        return bool((await self._session.execute(select(or_(paid, shared, settled)))).scalar())

    async def update_ledger(self, row: ExpenseLedger, **values: Any) -> ExpenseLedger:
        """@brief Apply column changes."""
        for k, v in values.items():
            setattr(row, k, v)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    # --- expenses ----------------------------------------------------------
    async def add_expense(
        self, ledger_id: uuid.UUID, shares: dict[uuid.UUID, int], **values: Any
    ) -> Expense:
        """@brief Insert an expense with its shares."""
        row = Expense(ledger_id=ledger_id, **values)
        self._session.add(row)
        await self._session.flush()
        for uid, cents in shares.items():
            self._session.add(ExpenseShare(expense_id=row.id, user_id=uid, amount_cents=cents))
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_expense(self, ledger_id: uuid.UUID, expense_id: uuid.UUID) -> Expense | None:
        """@brief Live expense of the ledger."""
        stmt = select(Expense).where(
            Expense.id == expense_id, Expense.ledger_id == ledger_id, Expense.deleted_at.is_(None)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def soft_delete_expense(self, row: Expense) -> None:
        """@brief Mark deleted."""
        row.deleted_at = datetime.now(UTC)
        await self._session.flush()

    async def expenses(self, ledger_id: uuid.UUID) -> list[Expense]:
        """@brief Live expenses, newest first."""
        stmt = (
            select(Expense)
            .where(Expense.ledger_id == ledger_id, Expense.deleted_at.is_(None))
            .order_by(Expense.spent_on.desc(), Expense.created_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars())

    async def shares(self, expense_ids: list[uuid.UUID]) -> list[ExpenseShare]:
        """@brief Shares of the given expenses."""
        if not expense_ids:
            return []
        stmt = select(ExpenseShare).where(ExpenseShare.expense_id.in_(expense_ids))
        return list((await self._session.execute(stmt)).scalars())

    async def settlements(self, ledger_id: uuid.UUID) -> list[Settlement]:
        """@brief All settlements of the ledger."""
        stmt = select(Settlement).where(Settlement.ledger_id == ledger_id)
        return list((await self._session.execute(stmt)).scalars())

    async def add_settlement(self, ledger_id: uuid.UUID, **values: Any) -> Settlement:
        """@brief Insert a settlement."""
        row = Settlement(ledger_id=ledger_id, **values)
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    # --- users / links -----------------------------------------------------
    async def usable_users(
        self, user_ids: list[uuid.UUID], viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> set[uuid.UUID]:
        """@brief Of ``user_ids``: live, not memorialized, not blocked with the viewer."""
        if not user_ids:
            return set()
        stmt = select(User.id).where(
            User.id.in_(user_ids),
            User.community_id == community_id,
            User.deleted_at.is_(None),
            User.memorialized_at.is_(None),
            not_blocked(User.id, viewer_id),
        )
        return set((await self._session.execute(stmt)).scalars())

    async def blocked_with(self, user_ids: list[uuid.UUID], viewer_id: uuid.UUID) -> set[uuid.UUID]:
        """@brief Of ``user_ids``: those in a block relation with the viewer."""
        if not user_ids:
            return set()
        stmt = select(User.id).where(User.id.in_(user_ids), ~not_blocked(User.id, viewer_id))
        return set((await self._session.execute(stmt)).scalars())

    async def notifiable(self, user_ids: list[uuid.UUID], actor_id: uuid.UUID) -> list[uuid.UUID]:
        """@brief Of ``user_ids``: live, not memorialized, not blocked with the actor."""
        if not user_ids:
            return []
        stmt = select(User.id).where(
            User.id.in_(user_ids),
            User.deleted_at.is_(None),
            User.memorialized_at.is_(None),
            not_blocked(User.id, actor_id),
        )
        ok = set((await self._session.execute(stmt)).scalars())
        return [u for u in user_ids if u in ok]

    async def names(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        """@brief Display names."""
        if not user_ids:
            return {}
        stmt = select(User.id, User.display_name).where(User.id.in_(user_ids))
        return {i: n for i, n in (await self._session.execute(stmt)).all()}

    async def event_viewable(
        self, event_id: uuid.UUID, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> bool:
        """@brief Event exists and the viewer may see it (community, own, or their group)."""
        in_group = exists().where(
            SubgroupMember.subgroup_id == Event.subgroup_id, SubgroupMember.user_id == viewer_id
        )
        stmt = select(Event.id).where(
            Event.id == event_id,
            Event.community_id == community_id,
            or_(
                Event.visibility == "community",
                and_(Event.visibility == "private", Event.author_id == viewer_id),
                and_(Event.visibility == "subgroup", in_group),
            ),
        )
        return (await self._session.execute(stmt)).first() is not None

    async def wishlist_viewable(
        self, wishlist_id: uuid.UUID, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> bool:
        """@brief Wishlist is visible to the viewer."""
        stmt = select(Wishlist.id).where(
            Wishlist.id == wishlist_id, wishlist_visible(viewer_id, community_id)
        )
        return (await self._session.execute(stmt)).first() is not None

    async def wishlist_item_viewable(
        self, item_id: uuid.UUID, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> tuple[uuid.UUID, str] | None:
        """@brief ``(wishlist_id, name)`` of a live item the viewer can see, else None."""
        stmt = (
            select(WishlistItem.wishlist_id, WishlistItem.name)
            .join(Wishlist, Wishlist.id == WishlistItem.wishlist_id)
            .where(
                WishlistItem.id == item_id,
                WishlistItem.deleted_at.is_(None),
                wishlist_visible(viewer_id, community_id),
            )
        )
        row = (await self._session.execute(stmt)).first()
        return (row[0], row[1]) if row else None

    async def wishlist_ledger(
        self, wishlist_id: uuid.UUID, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> ExpenseLedger | None:
        """@brief The viewer's newest live ledger tied to the wishlist."""
        rows = await self.list_ledgers(community_id, viewer_id, wishlist_id=wishlist_id)
        return next((r for r, _n in rows if r.archived_at is None), None)
