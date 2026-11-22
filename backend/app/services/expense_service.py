"""
@file expense_service.py
@brief Shared expense ledgers: members-only (non-members get 404 for
       everything), equal/custom splits, balances, simplified debts and
       serialized settlements. Money is integer cents.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.features import require_feature
from app.core.i18n import _
from app.models.expense import ExpenseLedger
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.expense_repo import ExpenseRepository
from app.schemas.expense import (
    CURRENCIES,
    BalanceOut,
    ExpenseIn,
    ExpenseOut,
    LedgerIn,
    LedgerOut,
    LedgerSummary,
    LedgerUpdate,
    MemberOut,
    SettleIn,
    ShareOut,
    TransferOut,
)
from app.services.expense_math import equal_split, net_balances, simplify
from app.services.notification_service import NotificationService


def _invalid(message: str, code: str = "VALIDATION_ERROR") -> AppError:
    return AppError(code, message, 422)


def _conflict(message: str, code: str = "CONFLICT") -> AppError:
    return AppError(code, message, 409)


class ExpenseService:
    """@brief Business rules for expense ledgers."""

    def __init__(
        self,
        repo: ExpenseRepository,
        community_repo: CommunityRepository,
        notifications: NotificationService | None,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = repo
        self._communities = community_repo
        self._notify = notifications
        self._community_id = community_id

    async def _community_currency(self, *, check: bool = True) -> str:
        community = await self._communities.get(self._community_id)
        if community is None:
            return "USD"
        if check:
            require_feature(community, "expenses")
        return str(community.currency or "USD").strip()

    async def _ledger(
        self, ledger_id: uuid.UUID, actor: User, *, lock: bool = False
    ) -> ExpenseLedger:
        """@brief Feature check, then the ledger; non-members get 404."""
        await self._community_currency()
        row = await self._repo.get_ledger(ledger_id, self._community_id, lock=lock)
        if row is None or not await self._repo.is_member(ledger_id, actor.id):
            raise NotFoundError(_("Ledger not found"))
        return row

    @staticmethod
    def _can_manage(ledger: ExpenseLedger, actor: User) -> bool:
        return ledger.created_by == actor.id or actor.role == "admin"

    # --- community currency -------------------------------------------------
    async def get_currency(self) -> str:
        """@return The community default currency."""
        return await self._community_currency(check=False)

    async def set_currency(self, code: str) -> str:
        """
        @brief Admin: change the community currency (existing ledgers keep theirs).
        @throws AppError 422 on an unsupported code.
        """
        if code not in CURRENCIES:
            raise _invalid(_("Unsupported currency"))
        await self._communities.update_currency(self._community_id, code)
        return code

    # --- ledgers ------------------------------------------------------------
    async def create_ledger(self, actor: User, body: LedgerIn) -> LedgerOut:
        """@brief Create a ledger; others must be live, unblocked, non-memorialized."""
        default = await self._community_currency()
        name = body.name.strip()
        if not name:
            raise _invalid(_("Give the ledger a name"))
        currency = body.currency or default
        if currency not in CURRENCIES:
            raise _invalid(_("Unsupported currency"))
        others = [u for u in dict.fromkeys(body.member_ids) if u != actor.id]
        if await self._repo.usable_users(others, actor.id, self._community_id) != set(others):
            raise _invalid(_("Unknown member"))
        if body.event_id and not await self._repo.event_viewable(
            body.event_id, actor.id, self._community_id
        ):
            raise NotFoundError(_("Event not found"))
        if body.wishlist_id and not await self._repo.wishlist_viewable(
            body.wishlist_id, actor.id, self._community_id
        ):
            raise NotFoundError(_("Wishlist not found"))
        row = await self._repo.create_ledger(
            self._community_id,
            [actor.id, *others],
            name=name,
            currency=currency,
            event_id=body.event_id,
            wishlist_id=body.wishlist_id,
            created_by=actor.id,
        )
        return await self._out(row, actor)

    async def from_wishlist_item(self, item_id: uuid.UUID, actor: User) -> LedgerOut:
        """@brief "Split this gift": reuse the viewer's ledger for the wishlist, else create."""
        await self._community_currency()
        found = await self._repo.wishlist_item_viewable(item_id, actor.id, self._community_id)
        if found is None:
            raise NotFoundError(_("Wishlist item not found"))
        wishlist_id, item_name = found
        row = await self._repo.wishlist_ledger(wishlist_id, actor.id, self._community_id)
        if row is None:
            row = await self._repo.create_ledger(
                self._community_id,
                [actor.id],
                name=item_name.strip()[:80] or _("Gift"),
                currency=await self._community_currency(),
                wishlist_id=wishlist_id,
                created_by=actor.id,
            )
        return await self._out(row, actor)

    async def list_ledgers(
        self,
        actor: User,
        event_id: uuid.UUID | None = None,
        wishlist_id: uuid.UUID | None = None,
    ) -> list[LedgerSummary]:
        """@brief Only the actor's own ledgers."""
        await self._community_currency()
        rows = await self._repo.list_ledgers(
            self._community_id, actor.id, event_id=event_id, wishlist_id=wishlist_id
        )
        return [self._summary(r, n) for r, n in rows]

    async def get_ledger(self, ledger_id: uuid.UUID, actor: User) -> LedgerOut:
        """@brief Full ledger for a member."""
        return await self._out(await self._ledger(ledger_id, actor), actor)

    async def update_ledger(
        self, ledger_id: uuid.UUID, actor: User, body: LedgerUpdate
    ) -> LedgerOut:
        """@brief Rename/archive (creator or admin member)."""
        row = await self._ledger(ledger_id, actor)
        if not self._can_manage(row, actor):
            raise AuthorizationError(_("Only the ledger creator can change it"))
        values: dict[str, Any] = {}
        if body.name is not None:
            if not body.name.strip():
                raise _invalid(_("Give the ledger a name"))
            values["name"] = body.name.strip()
        if body.archived is not None:
            values["archived_at"] = datetime.now(UTC) if body.archived else None
        if values:
            row = await self._repo.update_ledger(row, **values)
        return await self._out(row, actor)

    async def add_members(
        self, ledger_id: uuid.UUID, actor: User, user_ids: list[uuid.UUID]
    ) -> LedgerOut:
        """@brief Add members (creator or admin); same eligibility as creation."""
        row = await self._ledger(ledger_id, actor)
        if not self._can_manage(row, actor):
            raise AuthorizationError(_("Only the ledger creator can add people"))
        ids = list(dict.fromkeys(user_ids))
        if await self._repo.usable_users(ids, actor.id, self._community_id) != set(ids):
            raise _invalid(_("Unknown member"))
        await self._repo.add_members(ledger_id, ids)
        return await self._out(row, actor)

    async def remove_member(self, ledger_id: uuid.UUID, actor: User, user_id: uuid.UUID) -> None:
        """@brief Creator/admin removes anyone; a member may leave. Only when no activity."""
        row = await self._ledger(ledger_id, actor)
        if user_id != actor.id and not self._can_manage(row, actor):
            raise AuthorizationError(_("Only the ledger creator can remove people"))
        if not await self._repo.is_member(ledger_id, user_id):
            raise NotFoundError(_("Member not found"))
        if await self._repo.has_activity(ledger_id, user_id):
            raise _conflict(_("This person still has costs in the ledger"), "MEMBER_HAS_ACTIVITY")
        await self._repo.remove_member(ledger_id, user_id)

    # --- expenses -----------------------------------------------------------
    async def add_expense(self, ledger_id: uuid.UUID, actor: User, body: ExpenseIn) -> LedgerOut:
        """
        @brief Record an expense. Payer and sharers must be members; custom
               shares must sum exactly to the amount (``SHARES_MISMATCH``).
        """
        row = await self._ledger(ledger_id, actor)
        if row.archived_at is not None:
            raise _conflict(_("This ledger is archived"), "LEDGER_ARCHIVED")
        members = await self._repo.member_ids(ledger_id)
        if body.payer_id not in members:
            raise _invalid(_("The payer must be a member"))
        description = body.description.strip()
        if not description:
            raise _invalid(_("Describe the expense"))
        shares = self._shares(body, members)
        exp = await self._repo.add_expense(
            ledger_id,
            shares,
            payer_id=body.payer_id,
            amount_cents=body.amount_cents,
            description=description,
            spent_on=body.spent_on,
            created_by=actor.id,
        )
        await self._notify_added(row, actor, {body.payer_id, *shares}, exp.id)
        return await self._out(row, actor)

    @staticmethod
    def _shares(body: ExpenseIn, members: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        if body.split == "equal":
            among = list(dict.fromkeys(body.split_among or members))
            if not among or not set(among) <= set(members):
                raise _invalid(_("Everyone splitting must be a member"))
            return equal_split(body.amount_cents, among)
        custom = body.shares or []
        ids = [s.user_id for s in custom]
        if not custom or len(set(ids)) != len(ids) or not set(ids) <= set(members):
            raise _invalid(_("Everyone splitting must be a member"))
        if sum(s.amount_cents for s in custom) != body.amount_cents:
            raise _invalid(_("The shares must add up to the amount"), "SHARES_MISMATCH")
        return {s.user_id: s.amount_cents for s in custom}

    async def _notify_added(
        self, ledger: ExpenseLedger, actor: User, involved: set[uuid.UUID], expense_id: uuid.UUID
    ) -> None:
        """@brief Tell involved members; never blocked or memorialized users."""
        if self._notify is None:
            return
        targets = await self._repo.notifiable(sorted(involved - {actor.id}), actor.id)
        for uid in targets:
            await self._notify.notify(
                uid,
                "expense_added",
                {
                    "message": _("%(name)s added a cost to %(ledger)s")
                    % {"name": actor.display_name, "ledger": ledger.name},
                    "link": f"/app/expenses/{ledger.id}",
                    "ledger_id": str(ledger.id),
                    "ledger_name": ledger.name,
                    "actor_name": actor.display_name,
                },
                actor.id,
            )

    async def delete_expense(
        self, ledger_id: uuid.UUID, expense_id: uuid.UUID, actor: User
    ) -> LedgerOut:
        """@brief Delete (adder, payer, ledger creator or admin)."""
        row = await self._ledger(ledger_id, actor)
        exp = await self._repo.get_expense(ledger_id, expense_id)
        if exp is None:
            raise NotFoundError(_("Expense not found"))
        if actor.id not in (exp.created_by, exp.payer_id) and not self._can_manage(row, actor):
            raise AuthorizationError(_("You cannot delete this expense"))
        await self._repo.soft_delete_expense(exp)
        return await self._out(row, actor)

    async def settle(self, ledger_id: uuid.UUID, actor: User, body: SettleIn) -> LedgerOut:
        """
        @brief Record a payment. The ledger row is locked ``FOR UPDATE`` so two
               concurrent settles cannot both apply; the amount may not exceed
               what ``from`` owes or what ``to`` is owed.
        """
        row = await self._ledger(ledger_id, actor, lock=True)
        if actor.id not in (body.from_user_id, body.to_user_id):
            raise AuthorizationError(_("Only the payer or the payee can settle"))
        members = set(await self._repo.member_ids(ledger_id))
        if (
            body.from_user_id == body.to_user_id
            or not {body.from_user_id, body.to_user_id} <= members
        ):
            raise _invalid(_("Pick two different members"))
        bal = await self._balances(ledger_id)
        owes = -bal.get(body.from_user_id, 0)
        owed = bal.get(body.to_user_id, 0)
        if owes <= 0 or owed <= 0 or body.amount_cents > min(owes, owed):
            raise _conflict(_("That is more than is owed"), "SETTLE_EXCEEDS_BALANCE")
        await self._repo.add_settlement(
            ledger_id,
            from_user_id=body.from_user_id,
            to_user_id=body.to_user_id,
            amount_cents=body.amount_cents,
            created_by=actor.id,
        )
        return await self._out(row, actor)

    # --- views --------------------------------------------------------------
    async def _balances(self, ledger_id: uuid.UUID) -> dict[uuid.UUID, int]:
        exps = await self._repo.expenses(ledger_id)
        shares = await self._repo.shares([e.id for e in exps])
        sett = await self._repo.settlements(ledger_id)
        return net_balances(
            [(e.id, e.payer_id, e.amount_cents) for e in exps],
            [(s.expense_id, s.user_id, s.amount_cents) for s in shares],
            [(s.from_user_id, s.to_user_id, s.amount_cents) for s in sett],
        )

    @staticmethod
    def _summary(row: ExpenseLedger, count: int) -> LedgerSummary:
        return LedgerSummary(
            id=row.id,
            name=row.name,
            currency=row.currency,
            event_id=row.event_id,
            wishlist_id=row.wishlist_id,
            member_count=count,
            archived=row.archived_at is not None,
            created_at=row.created_at,
        )

    async def _out(self, row: ExpenseLedger, actor: User) -> LedgerOut:
        """@brief Serialize; names of users blocked with the viewer are masked."""
        members = await self._repo.member_ids(row.id)
        exps = await self._repo.expenses(row.id)
        shares = await self._repo.shares([e.id for e in exps])
        sett = await self._repo.settlements(row.id)
        bal = net_balances(
            [(e.id, e.payer_id, e.amount_cents) for e in exps],
            [(s.expense_id, s.user_id, s.amount_cents) for s in shares],
            [(s.from_user_id, s.to_user_id, s.amount_cents) for s in sett],
        )
        ids = list({*members, *bal, *(e.payer_id for e in exps)})
        raw = await self._repo.names(ids)
        hidden = await self._repo.blocked_with(ids, actor.id)

        def name(uid: uuid.UUID) -> str:
            return (
                _("Unavailable member") if uid in hidden else raw.get(uid, _("Unavailable member"))
            )

        by_exp: dict[uuid.UUID, list[ShareOut]] = {}
        for s in shares:
            by_exp.setdefault(s.expense_id, []).append(
                ShareOut(user_id=s.user_id, name=name(s.user_id), amount_cents=s.amount_cents)
            )
        out = self._summary(row, len(members)).model_dump()
        return LedgerOut(
            **out,
            created_by=row.created_by,
            can_manage=self._can_manage(row, actor),
            members=[MemberOut(user_id=u, name=name(u)) for u in members],
            balances=[BalanceOut(user_id=u, name=name(u), cents=bal.get(u, 0)) for u in members],
            transfers=[
                TransferOut(
                    from_user_id=f, from_name=name(f), to_user_id=t, to_name=name(t), cents=c
                )
                for f, t, c in simplify(bal)
            ],
            expenses=[
                ExpenseOut(
                    id=e.id,
                    payer_id=e.payer_id,
                    payer_name=name(e.payer_id),
                    amount_cents=e.amount_cents,
                    description=e.description,
                    spent_on=e.spent_on,
                    created_at=e.created_at,
                    shares=by_exp.get(e.id, []),
                )
                for e in exps
            ],
        )
