"""
@file test_push_device_service.py
@brief Unit tests for PushService native device-token registration.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, NotFoundError
from app.models.device_token import DeviceToken
from app.repositories.device_token_repo import DeviceTokenRepo
from app.services.push_service import PushService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()


@pytest.fixture
def device_repo():
    return AsyncMock(spec=DeviceTokenRepo)


@pytest.fixture
def service(device_repo):
    return PushService(
        push_repo=AsyncMock(),
        settings_repo=AsyncMock(),
        community_id=COMMUNITY_ID,
        settings=MagicMock(),
        device_repo=device_repo,
    )


class TestRegisterDevice:
    async def test_creates_when_token_unknown(self, service, device_repo):
        device_repo.find_by_token.return_value = None
        created = MagicMock(spec=DeviceToken)
        device_repo.create.return_value = created

        result = await service.register_device(USER_ID, "android", "tok")

        assert result is created
        device = device_repo.create.await_args.args[0]
        assert device.user_id == USER_ID
        assert device.community_id == COMMUNITY_ID
        assert device.platform == "android"
        assert device.token == "tok"

    async def test_reassigns_existing_token(self, service, device_repo):
        existing = MagicMock(spec=DeviceToken)
        device_repo.find_by_token.return_value = existing
        device_repo.reassign.return_value = existing

        result = await service.register_device(USER_ID, "ios", "tok")

        assert result is existing
        device_repo.reassign.assert_awaited_once_with(
            existing, user_id=USER_ID, community_id=COMMUNITY_ID, platform="ios"
        )
        device_repo.create.assert_not_awaited()


class TestUnregisterDevice:
    async def test_soft_deletes_own_token(self, service, device_repo):
        device = MagicMock(spec=DeviceToken)
        device_repo.find_active.return_value = device

        await service.unregister_device(USER_ID, "tok")

        device_repo.find_active.assert_awaited_once_with(COMMUNITY_ID, USER_ID, "tok")
        device_repo.soft_delete.assert_awaited_once_with(device)

    async def test_404_when_not_owned(self, service, device_repo):
        device_repo.find_active.return_value = None

        with pytest.raises(NotFoundError):
            await service.unregister_device(USER_ID, "tok")
        device_repo.soft_delete.assert_not_awaited()


class TestMissingDeviceRepo:
    async def test_register_raises_app_error_without_repo(self):
        svc = PushService(
            push_repo=AsyncMock(),
            settings_repo=AsyncMock(),
            community_id=COMMUNITY_ID,
            settings=MagicMock(),
        )
        with pytest.raises(AppError):
            await svc.register_device(USER_ID, "ios", "tok")

    async def test_unregister_raises_app_error_without_repo(self):
        svc = PushService(
            push_repo=AsyncMock(),
            settings_repo=AsyncMock(),
            community_id=COMMUNITY_ID,
            settings=MagicMock(),
        )
        with pytest.raises(AppError):
            await svc.unregister_device(USER_ID, "tok")
