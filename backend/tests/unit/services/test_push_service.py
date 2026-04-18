"""
@file test_push_service.py
@brief Unit tests for PushService.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.notification import PushSubscription
from app.repositories.push_repo import PushSubscriptionRepository
from app.services.push_service import PushService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()


@pytest.fixture
def push_repo():
    return AsyncMock(spec=PushSubscriptionRepository)


@pytest.fixture
def settings_repo():
    return AsyncMock()


@pytest.fixture
def service(push_repo, settings_repo):
    settings = MagicMock()
    settings.VAPID_PRIVATE_KEY = "test-private-key"
    settings.VAPID_PUBLIC_KEY = "test-public-key"
    settings.SMTP_FROM = "noreply@example.com"
    return PushService(
        push_repo=push_repo,
        settings_repo=settings_repo,
        community_id=COMMUNITY_ID,
        settings=settings,
    )


class TestSubscribe:
    @pytest.mark.asyncio
    async def test_subscribe_stores_subscription(self, service, push_repo):
        push_repo.find_by_endpoint.return_value = None
        new_sub = MagicMock(spec=PushSubscription)
        push_repo.create.return_value = new_sub

        result = await service.subscribe(
            USER_ID, "https://push.example.com/sub1", "p256dh-key", "auth-key", "Chrome"
        )

        assert result is new_sub
        push_repo.create.assert_awaited_once()


class TestUnsubscribe:
    @pytest.mark.asyncio
    async def test_unsubscribe_removes_subscription(self, service, push_repo):
        push_repo.delete_by_endpoint.return_value = True

        await service.unsubscribe(USER_ID, "https://push.example.com/sub1")

        push_repo.delete_by_endpoint.assert_awaited_once()


class TestSendPush:
    @pytest.mark.asyncio
    async def test_send_push_calls_webpush(self, service, push_repo):
        sub = MagicMock(spec=PushSubscription)
        sub.endpoint = "https://push.example.com/sub1"
        sub.p256dh = "p256dh-key"
        sub.auth = "auth-key"
        push_repo.list_for_user.return_value = [sub]

        with patch("pywebpush.webpush") as mock_webpush:
            await service.send_push(USER_ID, "Title", "Body", "/posts/1")
            mock_webpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_push_removes_on_410(self, service, push_repo):
        from pywebpush import WebPushException

        sub = MagicMock(spec=PushSubscription)
        sub.endpoint = "https://push.example.com/stale"
        sub.p256dh = "key"
        sub.auth = "auth"
        push_repo.list_for_user.return_value = [sub]

        mock_response = MagicMock()
        mock_response.status_code = 410

        with patch("pywebpush.webpush") as mock_webpush:
            mock_webpush.side_effect = WebPushException("Gone", response=mock_response)
            await service.send_push(USER_ID, "Title", "Body", "/")
            push_repo.cleanup_stale.assert_awaited_once_with(sub.endpoint)


class TestShouldSendPush:
    @pytest.mark.asyncio
    async def test_push_skipped_when_mute_all(self, service, settings_repo):
        settings = MagicMock()
        settings.mute_all_push = True
        settings_repo.get_by_user_id.return_value = settings

        result = await service.should_send_push(USER_ID, "mention")
        assert result is False

    @pytest.mark.asyncio
    async def test_push_skipped_when_type_disabled(self, service, settings_repo):
        settings = MagicMock()
        settings.mute_all_push = False
        settings.notif_mention_push = False
        settings_repo.get_by_user_id.return_value = settings

        result = await service.should_send_push(USER_ID, "mention")
        assert result is False
