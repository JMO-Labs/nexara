"""
@file test_settings_appearance.py
@brief Unit tests: home_pattern / reduce_transparency via PUT /api/v1/settings/.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.schemas.settings import UserSettingsResponse

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _response(**extra) -> UserSettingsResponse:
    """@brief Build a minimal UserSettingsResponse."""
    base = {
        "notif_mention_inapp": True,
        "notif_mention_email": True,
        "notif_comment_inapp": True,
        "notif_comment_email": True,
        "notif_reaction_inapp": True,
        "notif_reaction_email": False,
        "notif_new_post_inapp": True,
        "notif_new_post_email": False,
        "notif_system_inapp": True,
        "notif_system_email": True,
        "notif_invite_accepted_inapp": True,
        "notif_invite_accepted_email": False,
        "mute_all_email": False,
        "theme": "system",
        "locale": "en-US",
    }
    return UserSettingsResponse(**{**base, **extra})


def _setup(test_app, mock_service: AsyncMock) -> None:
    """@brief Override auth + service dependencies."""
    from app.api.v1 import settings as settings_module
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.community_id = COMMUNITY_ID

    async def _override_user():
        return user

    test_app.dependency_overrides[get_current_user] = _override_user
    test_app.dependency_overrides[settings_module._build_service] = lambda: mock_service


@pytest.mark.asyncio
async def test_settings_accepts_pattern_and_transparency(test_app):
    """PUT accepts home_pattern + reduce_transparency and echoes them."""
    svc = AsyncMock()
    svc.update_settings.return_value = _response(home_pattern="waves", reduce_transparency=True)
    _setup(test_app, svc)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            r = await client.put(
                "/api/v1/settings/",
                json={"home_pattern": "waves", "reduce_transparency": True},
            )
        assert r.status_code == 200
        assert r.json()["home_pattern"] == "waves"
        assert r.json()["reduce_transparency"] is True
    finally:
        test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_settings_rejects_unknown_pattern(test_app):
    """PUT rejects a pattern outside the allowed set."""
    _setup(test_app, AsyncMock())
    try:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            r = await client.put("/api/v1/settings/", json={"home_pattern": "plaid"})
        assert r.status_code == 422
    finally:
        test_app.dependency_overrides.clear()
