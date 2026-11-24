"""
@file test_plugin_tasks.py
@brief Signed delivery, retry policy and queue wiring for plugin webhooks.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import get_settings
from app.core.encryption import derive_fernet_key, encrypt_secret
from app.plugins.signing import verify
from app.tasks.celery_app import celery_app
from app.tasks.plugin_tasks import deliver_plugin_event

ROOT = Path(__file__).resolve().parents[4]


def _args():
    enc = encrypt_secret("topsecret", derive_fernet_key(get_settings().SECRET_KEY))
    return ("https://p.example/events", enc, '{"a":1}', "d-1")


def test_delivery_sends_signature_headers():
    post = AsyncMock(return_value=200)
    with patch("app.tasks.plugin_tasks._post", post):
        deliver_plugin_event.apply(args=_args()).get()
    _, body, headers = post.call_args.args
    assert headers["X-Nexara-Delivery"] == "d-1"
    ts = int(headers["X-Nexara-Timestamp"])
    assert verify("topsecret", ts, body, headers["X-Nexara-Signature"], now=ts)


def test_delivery_retries_on_500():
    post = AsyncMock(return_value=500)
    with patch("app.tasks.plugin_tasks._post", post):
        res = deliver_plugin_event.apply(args=_args())
    assert res.failed()
    assert post.call_count == 6  # first try + 5 retries


@pytest.mark.parametrize("status", [400, 404])
def test_delivery_no_retry_on_4xx(status):
    post = AsyncMock(return_value=status)
    with patch("app.tasks.plugin_tasks._post", post):
        deliver_plugin_event.apply(args=_args())
    assert post.call_count == 1


def test_delivery_retries_on_429():
    post = AsyncMock(return_value=429)
    with patch("app.tasks.plugin_tasks._post", post):
        deliver_plugin_event.apply(args=_args())
    assert post.call_count == 6


def test_plugins_queue_routed_and_consumed():
    assert celery_app.conf.task_routes["app.tasks.plugin_tasks.*"]["queue"] == "plugins"
    sup = (ROOT / "deploy/supervisord/conf.d/celery-worker.conf").read_text()
    helm = (ROOT / "deploy/helm/nexara/values.yaml").read_text()
    assert "plugins" in next(line for line in sup.splitlines() if "-Q" in line)
    assert "plugins" in next(line for line in helm.splitlines() if "queues:" in line)
