"""
@file test_storage_usage.py
@brief Unit tests for StorageUsageService.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.user import User
from app.repositories.media_repo import MediaRepository
from app.repositories.user_repo import UserRepository
from app.services.storage.usage_service import StorageUsageService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _user(used: int = 100, quota: int = 1000) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.community_id = COMMUNITY_ID
    user.storage_used = used
    user.storage_quota = quota
    return user


def _svc(target: MagicMock | None):
    media_repo = AsyncMock(spec=MediaRepository)
    user_repo = AsyncMock(spec=UserRepository)
    user_repo.get_by_id.return_value = target
    media_repo.get_user_storage_by_type.return_value = {
        "photos": 1,
        "videos": 2,
        "documents": 3,
        "other": 4,
    }
    return StorageUsageService(media_repo, user_repo), media_repo, user_repo


class TestGetUsage:
    async def test_returns_usage_for_self(self):
        user = _user()
        svc, media_repo, _ = _svc(user)
        res = await svc.get_usage(user, user.id)
        assert res.used_bytes == 100
        assert res.quota_bytes == 1000
        assert res.by_type.videos == 2
        media_repo.get_user_storage_by_type.assert_awaited_once_with(user.id, COMMUNITY_ID)

    async def test_other_user_forbidden(self):
        target = _user()
        svc, media_repo, _ = _svc(target)
        with pytest.raises(AuthorizationError):
            await svc.get_usage(_user(), target.id)
        media_repo.get_user_storage_by_type.assert_not_awaited()

    async def test_unknown_user_not_found(self):
        svc, _, _ = _svc(None)
        with pytest.raises(NotFoundError):
            await svc.get_usage(_user(), uuid.uuid4())


class TestFromSession:
    def test_binds_repositories_to_session(self):
        session = MagicMock()
        svc = StorageUsageService.from_session(session)
        assert isinstance(svc._media_repo, MediaRepository)
        assert isinstance(svc._user_repo, UserRepository)
