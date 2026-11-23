"""
@file test_expense_math.py
@brief Unit tests for equal split, balances and debt simplification.
"""

import random
import uuid

from app.services.expense_math import equal_split, net_balances, simplify


def _ids(n: int) -> list[uuid.UUID]:
    return [uuid.UUID(int=i + 1) for i in range(n)]


def test_equal_split_remainder_goes_to_first():
    a, b, c = _ids(3)
    assert equal_split(1000, [a, b, c]) == {a: 334, b: 333, c: 333}


def test_equal_split_exact_and_two_remainder():
    a, b, c = _ids(3)
    assert equal_split(900, [a, b, c]) == {a: 300, b: 300, c: 300}
    assert equal_split(1001, [a, b, c]) == {a: 334, b: 334, c: 333}


def test_simplify_example():
    a, b, c = _ids(3)
    assert simplify({a: 50, b: -30, c: -20}) == [(b, a, 30), (c, a, 20)]


def test_simplify_empty_when_settled():
    a, b = _ids(2)
    assert simplify({a: 0, b: 0}) == []


def test_settlement_zeroes_balance():
    a, b = _ids(2)
    e = uuid.uuid4()
    bal = net_balances([(e, a, 1000)], [(e, a, 500), (e, b, 500)], [(b, a, 500)])
    assert bal[a] == 0 and bal[b] == 0


def test_random_ledgers_sum_zero_and_simplify_preserves_balances():
    rng = random.Random(1234)
    users = _ids(6)
    for _ in range(50):
        exps, shares, sett = [], [], []
        for _ in range(rng.randint(1, 8)):
            eid, payer = uuid.uuid4(), rng.choice(users)
            amount = rng.randint(1, 50_000)
            among = rng.sample(users, rng.randint(1, len(users)))
            exps.append((eid, payer, amount))
            shares += [(eid, u, c) for u, c in equal_split(amount, among).items()]
        for _ in range(rng.randint(0, 3)):
            src, dst = rng.sample(users, 2)
            sett.append((src, dst, rng.randint(1, 1000)))
        bal = net_balances(exps, shares, sett)
        assert sum(bal.values()) == 0
        after = dict(bal)
        for src, dst, cents in simplify(bal):
            assert cents > 0
            after[src] = after.get(src, 0) + cents
            after[dst] = after.get(dst, 0) - cents
        assert all(v == 0 for v in after.values())
