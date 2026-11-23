"""
@file expense_math.py
@brief Pure money maths for shared expenses. Integer cents only.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable


def equal_split(amount_cents: int, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """
    @brief Split evenly; the remainder goes +1 cent to the first members in order.
    @param amount_cents Total in cents.
    @param user_ids Ordered, distinct participants (non-empty).
    @return user id -> cents, summing exactly to ``amount_cents``.
    """
    base, rest = divmod(amount_cents, len(user_ids))
    return {uid: base + (1 if i < rest else 0) for i, uid in enumerate(user_ids)}


def net_balances(
    expenses: Iterable[tuple[uuid.UUID, uuid.UUID, int]],
    shares: Iterable[tuple[uuid.UUID, uuid.UUID, int]],
    settlements: Iterable[tuple[uuid.UUID, uuid.UUID, int]],
) -> dict[uuid.UUID, int]:
    """
    @brief Net position per user; positive means the user is owed money.
    @param expenses ``(expense_id, payer_id, amount_cents)``.
    @param shares ``(expense_id, user_id, amount_cents)``.
    @param settlements ``(from_user_id, to_user_id, amount_cents)``: from paid to.
    @return user id -> net cents (values always sum to 0).
    """
    bal: dict[uuid.UUID, int] = {}
    for _eid, payer, cents in expenses:
        bal[payer] = bal.get(payer, 0) + cents
    for _eid, uid, cents in shares:
        bal[uid] = bal.get(uid, 0) - cents
    for src, dst, cents in settlements:
        bal[src] = bal.get(src, 0) + cents
        bal[dst] = bal.get(dst, 0) - cents
    return bal


def simplify(balances: dict[uuid.UUID, int]) -> list[tuple[uuid.UUID, uuid.UUID, int]]:
    """
    @brief Greedy debt simplification: largest debtor pays largest creditor.
    @param balances Net balances (sum to 0).
    @return ``(from, to, cents)`` transfers; ties break on id for determinism.
    """
    debtors = {u: -c for u, c in balances.items() if c < 0}
    creditors = {u: c for u, c in balances.items() if c > 0}
    out: list[tuple[uuid.UUID, uuid.UUID, int]] = []
    while debtors and creditors:
        d = max(debtors, key=lambda u: (debtors[u], u.int))
        c = max(creditors, key=lambda u: (creditors[u], u.int))
        pay = min(debtors[d], creditors[c])
        out.append((d, c, pay))
        debtors[d] -= pay
        creditors[c] -= pay
        if debtors[d] == 0:
            del debtors[d]
        if creditors[c] == 0:
            del creditors[c]
    return out
