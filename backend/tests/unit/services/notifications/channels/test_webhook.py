"""@file Tests for the webhook channel, signing, delivery and Celery task."""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.models.notification import Notification
from app.models.webhook import WebhookSubscription
from app.repositories.webhook_repo import MAX_FAILURES, WebhookRepository
from app.services.notifications.channels.base import ChannelResult
from app.services.notifications.channels.webhook import WebhookChannel
from app.services.notifications.webhook_delivery import (
    SIGNATURE_HEADER,
    build_payload,
    deliver_webhook,
    sign,
)
from app.tasks.notification_tasks import webhook_deliver

TASK = "app.services.notifications.channels.webhook.webhook_deliver"
TS = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def _notif() -> MagicMock:
    n = MagicMock(spec=Notification)
    n.id = uuid4()
    n.user_id = uuid4()
    n.community_id = uuid4()
    n.type = "new_post"
    n.payload = {"message": "hi", "link": "/p/1"}
    n.actor_ids = [uuid4()]
    n.count = 2
    n.created_at = TS
    n.updated_at = TS
    return n


def _sub(failures: int = 0) -> MagicMock:
    s = MagicMock(spec=WebhookSubscription)
    s.id = uuid4()
    s.url = "https://hooks.example.com/x"
    s.secret = "s3cret"
    s.enabled = True
    s.failure_count = failures
    return s


# --- channel fanout ---------------------------------------------------------


async def test_fanout_enqueues_one_task_per_matching_sub() -> None:
    n, subs = _notif(), [_sub(), _sub()]
    repo = AsyncMock(spec=WebhookRepository)
    repo.list_matching.return_value = subs
    with patch(TASK) as task:
        res = await WebhookChannel(repo).send(n)
    assert res == ChannelResult(ok=True)
    repo.list_matching.assert_awaited_once_with(n.community_id, n.user_id, "new_post")
    assert [c.args for c in task.delay.call_args_list] == [
        (str(s.id), str(n.id)) for s in subs
    ]


async def test_no_subscriptions_is_skipped() -> None:
    repo = AsyncMock(spec=WebhookRepository)
    repo.list_matching.return_value = []
    with patch(TASK) as task:
        res = await WebhookChannel(repo).send(_notif())
    assert res == ChannelResult(ok=True, skipped_reason="no_subscriptions")
    task.delay.assert_not_called()


async def test_enqueue_failure_isolated_per_sub() -> None:
    repo = AsyncMock(spec=WebhookRepository)
    repo.list_matching.return_value = [_sub(), _sub()]
    with patch(TASK) as task:
        task.delay.side_effect = [RuntimeError("broker down"), None]
        res = await WebhookChannel(repo).send(_notif())
    assert res.ok
    assert task.delay.call_count == 2


async def test_repo_error_never_raises() -> None:
    repo = AsyncMock(spec=WebhookRepository)
    repo.list_matching.side_effect = RuntimeError("db")
    with patch(TASK):
        res = await WebhookChannel(repo).send(_notif())
    assert res.ok is False
    assert res.error == "db"


# --- payload + signature ----------------------------------------------------


def test_build_payload_fields() -> None:
    n = _notif()
    p = build_payload(n, "social")
    assert p == {
        "id": str(n.id),
        "type": "new_post",
        "category": "social",
        "user_id": str(n.user_id),
        "community_id": str(n.community_id),
        "payload": {"message": "hi", "link": "/p/1"},
        "actor_ids": [str(a) for a in n.actor_ids],
        "count": 2,
        "created_at": TS.isoformat(),
        "updated_at": TS.isoformat(),
    }


def test_sign_is_stripe_style_hmac_sha256() -> None:
    body = '{"a":1}'
    expected = hmac.new(b"s3cret", b'1700000000.{"a":1}', hashlib.sha256).hexdigest()
    assert sign(body, "s3cret", 1700000000) == f"t=1700000000,v1={expected}"


# --- delivery ---------------------------------------------------------------


def _client(status: int | Exception) -> tuple[httpx.AsyncClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        if isinstance(status, Exception):
            raise status
        return httpx.Response(status)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), seen


async def test_2xx_posts_signed_body_and_records_success() -> None:
    sub, n = _sub(), _notif()
    repo = AsyncMock(spec=WebhookRepository)
    client, seen = _client(204)
    with patch("app.services.notifications.webhook_delivery.time.time", return_value=1700000000):
        out = await deliver_webhook(repo, sub, n, "social", client, final_attempt=False)
    assert out == "delivered"
    req = seen[0]
    assert str(req.url) == sub.url
    body = req.content.decode()
    assert json.loads(body)["id"] == str(n.id)
    assert req.headers[SIGNATURE_HEADER] == sign(body, "s3cret", 1700000000)
    assert req.headers["content-type"] == "application/json"
    repo.record_success.assert_awaited_once_with(sub.id)
    repo.record_failure.assert_not_awaited()


async def test_4xx_records_failure_without_retry() -> None:
    sub = _sub()
    repo = AsyncMock(spec=WebhookRepository)
    client, _ = _client(404)
    out = await deliver_webhook(repo, sub, _notif(), "social", client, final_attempt=False)
    assert out == "failed"
    repo.record_failure.assert_awaited_once_with(sub.id)
    repo.record_success.assert_not_awaited()


async def test_4xx_at_threshold_logs_disabled() -> None:
    sub = _sub(failures=MAX_FAILURES - 1)
    repo = AsyncMock(spec=WebhookRepository)

    async def fail(_id: object) -> None:
        sub.failure_count += 1
        sub.enabled = sub.failure_count < MAX_FAILURES

    repo.record_failure.side_effect = fail
    client, _ = _client(410)
    with patch("app.services.notifications.webhook_delivery.logger") as log:
        out = await deliver_webhook(repo, sub, _notif(), "social", client, final_attempt=False)
    assert out == "disabled"
    events = [c.args[0] for c in log.warning.call_args_list]
    assert "webhook.disabled" in events
    assert "notif.channel.failed" in events


async def test_5xx_raises_for_retry_without_recording() -> None:
    repo = AsyncMock(spec=WebhookRepository)
    client, _ = _client(503)
    with pytest.raises(httpx.HTTPStatusError):
        await deliver_webhook(repo, _sub(), _notif(), "social", client, final_attempt=False)
    repo.record_failure.assert_not_awaited()


async def test_timeout_on_final_attempt_records_failure_and_raises() -> None:
    sub = _sub()
    repo = AsyncMock(spec=WebhookRepository)
    client, _ = _client(httpx.ReadTimeout("slow"))
    with pytest.raises(httpx.TimeoutException):
        await deliver_webhook(repo, sub, _notif(), "social", client, final_attempt=True)
    repo.record_failure.assert_awaited_once_with(sub.id)


# --- celery task config -----------------------------------------------------


def test_task_retry_config() -> None:
    assert webhook_deliver.max_retries == 5
    assert webhook_deliver.retry_backoff is True
    assert webhook_deliver.retry_backoff_max == 600
    assert webhook_deliver.retry_jitter is True
    assert set(webhook_deliver.autoretry_for) == {httpx.HTTPError, httpx.TimeoutException}
    assert webhook_deliver.queue == "notifications"


def test_task_runs_async_delivery() -> None:
    wid, nid = str(uuid4()), str(uuid4())
    with patch(
        "app.tasks.notification_tasks._webhook_deliver_async",
        new=AsyncMock(return_value={"status": "delivered"}),
    ) as impl:
        out = webhook_deliver.run(wid, nid)
    assert out == {"status": "delivered"}
    assert impl.await_args.args[:2] == (wid, nid)


def test_task_invalid_uuid_skipped() -> None:
    assert webhook_deliver.run("nope", "nope") == {"status": "skipped"}
