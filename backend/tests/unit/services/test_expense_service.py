"""
@file test_expense_service.py
@brief Unit tests for ExpenseService (AsyncMock repos).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.models.community import Community
from app.models.expense import Expense, ExpenseLedger, ExpenseShare, Settlement
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.expense_repo import ExpenseRepository
from app.schemas.expense import ExpenseIn, LedgerIn, SettleIn, ShareIn
from app.services.expense_service import ExpenseService
from app.services.notification_service import NotificationService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
A, B, C = (uuid.UUID(int=i) for i in (1, 2, 3))
LID = uuid.uuid4()


def _user(uid: uuid.UUID, role: str = "member") -> MagicMock:
    u = MagicMock(spec=User)
    u.id, u.role, u.display_name = uid, role, "Name"
    return u


def _ledger(created_by: uuid.UUID = A) -> MagicMock:
    r = MagicMock(spec=ExpenseLedger)
    r.id, r.name, r.currency, r.created_by = LID, "Trip", "USD", created_by
    r.event_id = r.wishlist_id = r.archived_at = None
    r.created_at = datetime.now(UTC)
    return r


@pytest.fixture
def svc():
    repo = AsyncMock(spec=ExpenseRepository)
    comm = AsyncMock(spec=CommunityRepository)
    community = MagicMock(spec=Community)
    community.features, community.currency = {}, "EUR"
    comm.get.return_value = community
    notif = AsyncMock(spec=NotificationService)
    repo.get_ledger.return_value = _ledger()
    repo.is_member.return_value = True
    repo.member_ids.return_value = [A, B, C]
    repo.expenses.return_value = []
    repo.shares.return_value = []
    repo.settlements.return_value = []
    repo.names.return_value = {A: "Ana", B: "Bo", C: "Cy"}
    repo.blocked_with.return_value = set()
    repo.notifiable.side_effect = lambda ids, _actor: ids
    return ExpenseService(repo, comm, notif, CID), repo, community, notif


def _body(**kw) -> ExpenseIn:
    base = {"payer_id": A, "amount_cents": 1000, "description": "Cabin", "spent_on": date.today()}
    return ExpenseIn(**{**base, **kw})


async def test_feature_disabled_blocks_every_entry(svc):
    s, _repo, community, _ = svc
    community.features = {"expenses": False}
    for call in (
        s.list_ledgers(_user(A)),
        s.get_ledger(LID, _user(A)),
        s.add_expense(LID, _user(A), _body()),
        s.settle(LID, _user(A), SettleIn(from_user_id=A, to_user_id=B, amount_cents=1)),
        s.create_ledger(_user(A), LedgerIn(name="x")),
    ):
        with pytest.raises(AppError) as e:
            await call
        assert e.value.status_code == 404


async def test_non_member_gets_404_everywhere(svc):
    s, repo, _, _ = svc
    repo.is_member.return_value = False
    outsider = _user(uuid.uuid4())
    for call in (
        s.get_ledger(LID, outsider),
        s.add_expense(LID, outsider, _body()),
        s.settle(LID, outsider, SettleIn(from_user_id=A, to_user_id=B, amount_cents=1)),
        s.add_members(LID, outsider, [B]),
        s.remove_member(LID, outsider, B),
        s.delete_expense(LID, uuid.uuid4(), outsider),
        s.update_ledger(LID, outsider, MagicMock()),
    ):
        with pytest.raises(NotFoundError):
            await call


async def test_unknown_ledger_404(svc):
    s, repo, _, _ = svc
    repo.get_ledger.return_value = None
    with pytest.raises(NotFoundError):
        await s.get_ledger(LID, _user(A))


async def test_equal_split_stored_with_remainder_and_notifies_others(svc):
    s, repo, _, notif = svc
    repo.add_expense.return_value = MagicMock(spec=Expense, id=uuid.uuid4())
    await s.add_expense(LID, _user(A), _body())
    shares = repo.add_expense.call_args.args[1]
    assert shares == {A: 334, B: 333, C: 333}
    notified = {c.args[0] for c in notif.notify.call_args_list}
    assert notified == {B, C}  # never the actor
    assert notif.notify.call_args.args[1] == "expense_added"


async def test_notifications_use_filter_for_blocked_and_memorialized(svc):
    s, repo, _, notif = svc
    repo.add_expense.return_value = MagicMock(spec=Expense, id=uuid.uuid4())
    repo.notifiable.side_effect = lambda ids, _a: [u for u in ids if u != B]
    await s.add_expense(LID, _user(A), _body())
    assert {c.args[0] for c in notif.notify.call_args_list} == {C}


async def test_custom_shares_mismatch_is_422(svc):
    s, _repo, _, _ = svc
    body = _body(
        split="custom",
        shares=[ShareIn(user_id=A, amount_cents=600), ShareIn(user_id=B, amount_cents=300)],
    )
    with pytest.raises(AppError) as e:
        await s.add_expense(LID, _user(A), body)
    assert (e.value.code, e.value.status_code) == ("SHARES_MISMATCH", 422)


async def test_custom_shares_exact_ok(svc):
    s, repo, _, _ = svc
    repo.add_expense.return_value = MagicMock(spec=Expense, id=uuid.uuid4())
    body = _body(
        split="custom",
        shares=[ShareIn(user_id=A, amount_cents=600), ShareIn(user_id=B, amount_cents=400)],
    )
    await s.add_expense(LID, _user(A), body)
    assert repo.add_expense.call_args.args[1] == {A: 600, B: 400}


async def test_payer_and_sharers_must_be_members(svc):
    s, _repo, _, _ = svc
    with pytest.raises(AppError):
        await s.add_expense(LID, _user(A), _body(payer_id=uuid.uuid4()))
    with pytest.raises(AppError):
        await s.add_expense(LID, _user(A), _body(split_among=[A, uuid.uuid4()]))


async def test_create_rejects_unusable_members_and_defaults_currency(svc):
    s, repo, _, _ = svc
    repo.usable_users.return_value = set()  # blocked / memorialized / foreign
    with pytest.raises(AppError):
        await s.create_ledger(_user(A), LedgerIn(name="x", member_ids=[B]))
    repo.usable_users.return_value = {B}
    repo.create_ledger.return_value = _ledger()
    await s.create_ledger(_user(A), LedgerIn(name="x", member_ids=[B]))
    assert repo.create_ledger.call_args.kwargs["currency"] == "EUR"
    assert repo.create_ledger.call_args.args[1] == [A, B]


async def test_create_with_invisible_event_is_404(svc):
    s, repo, _, _ = svc
    repo.usable_users.return_value = set()
    repo.event_viewable.return_value = False
    with pytest.raises(NotFoundError):
        await s.create_ledger(_user(A), LedgerIn(name="x", event_id=uuid.uuid4()))


def _owes(repo, amount=500):
    e = MagicMock(spec=Expense, id=uuid.uuid4(), payer_id=A, amount_cents=amount * 2)
    e.description, e.spent_on, e.created_at = "Cabin", date.today(), datetime.now(UTC)
    repo.expenses.return_value = [e]
    repo.shares.return_value = [
        MagicMock(spec=ExpenseShare, expense_id=e.id, user_id=A, amount_cents=amount),
        MagicMock(spec=ExpenseShare, expense_id=e.id, user_id=B, amount_cents=amount),
    ]


async def test_settle_reduces_balance_to_zero_and_locks(svc):
    s, repo, _, _ = svc
    _owes(repo)
    out0 = await s.get_ledger(LID, _user(A))
    assert {b.user_id: b.cents for b in out0.balances}[B] == -500
    repo.add_settlement.return_value = MagicMock(spec=Settlement)
    await s.settle(LID, _user(B), SettleIn(from_user_id=B, to_user_id=A, amount_cents=500))
    assert repo.get_ledger.call_args.kwargs["lock"] is True
    repo.settlements.return_value = [
        MagicMock(spec=Settlement, from_user_id=B, to_user_id=A, amount_cents=500)
    ]
    out = await s.get_ledger(LID, _user(A))
    assert all(b.cents == 0 for b in out.balances) and out.transfers == []


async def test_settle_cannot_double_apply_or_exceed(svc):
    s, repo, _, _ = svc
    _owes(repo)
    with pytest.raises(AppError) as e:
        await s.settle(LID, _user(B), SettleIn(from_user_id=B, to_user_id=A, amount_cents=501))
    assert e.value.code == "SETTLE_EXCEEDS_BALANCE"
    repo.settlements.return_value = [
        MagicMock(spec=Settlement, from_user_id=B, to_user_id=A, amount_cents=500)
    ]
    with pytest.raises(AppError):  # second apply of the same payment
        await s.settle(LID, _user(B), SettleIn(from_user_id=B, to_user_id=A, amount_cents=500))
    repo.add_settlement.assert_not_called()


async def test_settle_actor_must_be_party(svc):
    s, repo, _, _ = svc
    _owes(repo)
    with pytest.raises(AuthorizationError):
        await s.settle(LID, _user(C), SettleIn(from_user_id=B, to_user_id=A, amount_cents=100))


async def test_blocked_member_name_masked(svc):
    s, repo, _, _ = svc
    repo.blocked_with.return_value = {B}
    out = await s.get_ledger(LID, _user(A))
    assert "Bo" not in [m.name for m in out.members]
    assert [m.name for m in out.members if m.user_id == A] == ["Ana"]


async def test_remove_member_with_activity_conflicts(svc):
    s, repo, _, _ = svc
    repo.has_activity.return_value = True
    with pytest.raises(AppError) as e:
        await s.remove_member(LID, _user(A), B)
    assert e.value.status_code == 409


async def test_non_creator_cannot_add_members(svc):
    s, _repo, _, _ = svc
    with pytest.raises(AuthorizationError):
        await s.add_members(LID, _user(B), [C])


async def test_split_gift_reuses_existing_ledger(svc):
    s, repo, _, _ = svc
    wl = uuid.uuid4()
    repo.wishlist_item_viewable.return_value = (wl, "Lego set")
    repo.wishlist_ledger.return_value = _ledger()
    await s.from_wishlist_item(uuid.uuid4(), _user(A))
    repo.create_ledger.assert_not_called()
    repo.wishlist_ledger.return_value = None
    repo.create_ledger.return_value = _ledger()
    await s.from_wishlist_item(uuid.uuid4(), _user(A))
    assert repo.create_ledger.call_args.kwargs["wishlist_id"] == wl


async def test_split_gift_invisible_item_404(svc):
    s, repo, _, _ = svc
    repo.wishlist_item_viewable.return_value = None
    with pytest.raises(NotFoundError):
        await s.from_wishlist_item(uuid.uuid4(), _user(A))


async def test_set_currency_validates(svc):
    s, _repo, _, _ = svc
    with pytest.raises(AppError):
        await s.set_currency("XXX")
    assert await s.set_currency("GBP") == "GBP"
