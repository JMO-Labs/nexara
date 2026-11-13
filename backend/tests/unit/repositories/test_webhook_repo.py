"""
@file test_webhook_repo.py
@brief Unit tests for WebhookRepository (CRUD, matching, failure tracking).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.webhook import WebhookSubscription
from app.repositories.webhook_repo import MAX_FAILURES, WebhookRepository

CID, UID = uuid.uuid4(), uuid.uuid4()


def _repo(rows=None, one=None):
    session = AsyncMock()
    session.add = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows or []
    result.scalar_one_or_none.return_value = one
    session.execute.return_value = result
    session.get.return_value = one
    return WebhookRepository(session), session


def _sub(**kw):
    sub = MagicMock(spec=WebhookSubscription)
    sub.enabled, sub.failure_count, sub.last_failure_at = True, 0, None
    for k, v in kw.items():
        setattr(sub, k, v)
    return sub


async def test_create_adds_and_flushes():
    repo, session = _repo()
    out = await repo.create(CID, UID, "https://x.io/h", "s3cret", ["post.created"])
    added = session.add.call_args.args[0]
    assert (added.community_id, added.user_id, added.url) == (CID, UID, "https://x.io/h")
    assert added.secret == "s3cret" and added.type_keys == ["post.created"]
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(out)


async def test_get_returns_row():
    sub = _sub()
    repo, _ = _repo(one=sub)
    assert await repo.get(uuid.uuid4()) is sub


async def test_list_for_user_filters_user():
    repo, session = _repo(rows=[_sub()])
    assert len(await repo.list_for_user(UID)) == 1
    sql = str(session.execute.await_args.args[0])
    assert "webhook_subscriptions.user_id =" in sql


async def test_list_for_community_only_community_level():
    repo, session = _repo()
    await repo.list_for_community(CID)
    sql = str(session.execute.await_args.args[0])
    assert "webhook_subscriptions.community_id =" in sql
    assert "webhook_subscriptions.user_id IS NULL" in sql


async def test_list_matching_filters_enabled_scope_and_type():
    repo, session = _repo()
    await repo.list_matching(CID, UID, "post.created")
    sql = str(session.execute.await_args.args[0])
    assert "webhook_subscriptions.enabled" in sql
    assert "webhook_subscriptions.user_id IS NULL" in sql
    assert "webhook_subscriptions.user_id =" in sql
    assert "cardinality(webhook_subscriptions.type_keys)" in sql  # empty == all types
    assert "ANY (webhook_subscriptions.type_keys)" in sql


async def test_set_enabled_toggles():
    sub = _sub()
    repo, session = _repo(one=sub)
    out = await repo.set_enabled(uuid.uuid4(), False)
    assert out is sub and sub.enabled is False
    session.flush.assert_awaited()


async def test_update_partial_only_given_fields():
    sub = _sub(url="https://old", type_keys=["a"])
    repo, _ = _repo(one=sub)
    await repo.update(uuid.uuid4(), type_keys=["b"])
    assert sub.url == "https://old" and sub.type_keys == ["b"]
    await repo.update(uuid.uuid4(), url="https://new", enabled=False)
    assert sub.url == "https://new" and sub.enabled is False


async def test_update_missing_returns_none():
    repo, _ = _repo(one=None)
    assert await repo.update(uuid.uuid4(), url="https://n") is None


async def test_delete_removes_row():
    sub = _sub()
    repo, session = _repo(one=sub)
    assert await repo.delete(uuid.uuid4()) is True
    session.delete.assert_awaited_once_with(sub)


async def test_delete_missing_returns_false():
    repo, session = _repo(one=None)
    assert await repo.delete(uuid.uuid4()) is False
    session.delete.assert_not_awaited()


async def test_record_failure_increments_and_stays_enabled():
    sub = _sub(failure_count=2)
    repo, _ = _repo(one=sub)
    await repo.record_failure(uuid.uuid4())
    assert sub.failure_count == 3 and sub.enabled is True
    assert sub.last_failure_at is not None


async def test_record_failure_auto_disables_at_threshold():
    sub = _sub(failure_count=MAX_FAILURES - 1)
    repo, _ = _repo(one=sub)
    await repo.record_failure(uuid.uuid4())
    assert sub.failure_count == MAX_FAILURES and sub.enabled is False


async def test_record_success_resets_counter():
    sub = _sub(failure_count=5)
    repo, _ = _repo(one=sub)
    await repo.record_success(uuid.uuid4())
    assert sub.failure_count == 0
