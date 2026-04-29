"""
@file test_user_settings_home_layout.py
@brief Unit tests: round-trip home_layout via PUT /api/v1/settings/.

Verifies that the settings endpoint accepts a home_layout dict and
reflects it back in the response.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.schemas.settings import HomeLayoutSchema, WidgetInstanceSchema

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()

HOME_LAYOUT_PAYLOAD = {
    "widgets": [
        {"id": "abc-123", "defId": "feed", "size": "lg", "collapsed": False, "order": 0},
        {"id": "def-456", "defId": "upcoming-events", "size": "md", "collapsed": False, "order": 1},
    ]
}

HOME_LAYOUT_SCHEMA = HomeLayoutSchema(
    widgets=[
        WidgetInstanceSchema(id="abc-123", defId="feed", size="lg", collapsed=False, order=0),
        WidgetInstanceSchema(id="def-456", defId="upcoming-events", size="md", collapsed=False, order=1),
    ]
)


def _mock_user() -> MagicMock:
    """@brief Build a mock User for dependency injection."""
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = USER_ID
    user.community_id = COMMUNITY_ID
    return user


def _mock_settings_row(home_layout: dict | None = None) -> MagicMock:
    """@brief Build a mock UserSettings row."""
    row = MagicMock()
    row.user_id = USER_ID
    row.notif_mention_inapp = True
    row.notif_mention_email = True
    row.notif_comment_inapp = True
    row.notif_comment_email = True
    row.notif_reaction_inapp = True
    row.notif_reaction_email = False
    row.notif_new_post_inapp = True
    row.notif_new_post_email = False
    row.notif_system_inapp = True
    row.notif_system_email = True
    row.notif_invite_accepted_inapp = True
    row.notif_invite_accepted_email = False
    row.mute_all_email = False
    row.theme = "system"
    row.locale = "en-US"
    row.home_layout = home_layout
    return row


def _setup_auth_and_service(test_app, mock_service: AsyncMock):
    """@brief Override auth + service dependencies."""
    from app.api.v1 import settings as settings_module

    user = _mock_user()

    async def _override_user():
        return user

    def _override_service():
        return mock_service

    test_app.dependency_overrides[get_current_user] = _override_user
    test_app.dependency_overrides[settings_module._build_service] = _override_service
    return user


def _clear_overrides(test_app):
    """@brief Clear dependency overrides after each test."""
    test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_patch_home_layout_round_trip(test_app):
    """PUT /settings/ with home_layout payload reflects it in the response."""
    mock_svc = AsyncMock()
    mock_svc.update_settings.return_value = MagicMock(
        notif_mention_inapp=True,
        notif_mention_email=True,
        notif_comment_inapp=True,
        notif_comment_email=True,
        notif_reaction_inapp=True,
        notif_reaction_email=False,
        notif_new_post_inapp=True,
        notif_new_post_email=False,
        notif_system_inapp=True,
        notif_system_email=True,
        notif_invite_accepted_inapp=True,
        notif_invite_accepted_email=False,
        mute_all_email=False,
        theme="system",
        locale="en-US",
        home_layout=HOME_LAYOUT_PAYLOAD,
    )

    from app.schemas.settings import UserSettingsResponse

    mock_svc.update_settings.return_value = UserSettingsResponse(
        notif_mention_inapp=True,
        notif_mention_email=True,
        notif_comment_inapp=True,
        notif_comment_email=True,
        notif_reaction_inapp=True,
        notif_reaction_email=False,
        notif_new_post_inapp=True,
        notif_new_post_email=False,
        notif_system_inapp=True,
        notif_system_email=True,
        notif_invite_accepted_inapp=True,
        notif_invite_accepted_email=False,
        mute_all_email=False,
        theme="system",
        locale="en-US",
        home_layout=HOME_LAYOUT_SCHEMA,
    )

    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/settings/",
                json={"home_layout": HOME_LAYOUT_PAYLOAD},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "widgets" in data["home_layout"]
        assert len(data["home_layout"]["widgets"]) == 2
        # confirm service was called with the layout
        mock_svc.update_settings.assert_called_once()
        call_arg = mock_svc.update_settings.call_args[0][1]
        assert call_arg.home_layout is not None
        assert len(call_arg.home_layout.widgets) == 2
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_get_settings_includes_home_layout_field(test_app):
    """GET /settings/ response contains home_layout field (possibly None)."""
    from app.schemas.settings import UserSettingsResponse

    mock_svc = AsyncMock()
    mock_svc.get_settings.return_value = UserSettingsResponse(
        notif_mention_inapp=True,
        notif_mention_email=True,
        notif_comment_inapp=True,
        notif_comment_email=True,
        notif_reaction_inapp=True,
        notif_reaction_email=False,
        notif_new_post_inapp=True,
        notif_new_post_email=False,
        notif_system_inapp=True,
        notif_system_email=True,
        notif_invite_accepted_inapp=True,
        notif_invite_accepted_email=False,
        mute_all_email=False,
        theme="system",
        locale="en-US",
        home_layout=None,
    )

    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/settings/")
        assert resp.status_code == 200
        data = resp.json()
        assert "home_layout" in data
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_patch_home_layout_null_clears_layout(test_app):
    """PATCH home_layout=None → service receives None; GET reflects null field."""
    from app.schemas.settings import UserSettingsResponse

    mock_svc = AsyncMock()
    mock_svc.update_settings.return_value = UserSettingsResponse(
        notif_mention_inapp=True,
        notif_mention_email=True,
        notif_comment_inapp=True,
        notif_comment_email=True,
        notif_reaction_inapp=True,
        notif_reaction_email=False,
        notif_new_post_inapp=True,
        notif_new_post_email=False,
        notif_system_inapp=True,
        notif_system_email=True,
        notif_invite_accepted_inapp=True,
        notif_invite_accepted_email=False,
        mute_all_email=False,
        theme="system",
        locale="en-US",
        home_layout=None,
    )

    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/settings/",
                json={"home_layout": None},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["home_layout"] is None
        # Confirm service was called with explicit None
        mock_svc.update_settings.assert_called_once()
        call_arg = mock_svc.update_settings.call_args[0][1]
        assert call_arg.home_layout is None
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_patch_malformed_home_layout_returns_422(test_app):
    """PATCH with malformed home_layout (wrong field types) returns 422."""
    mock_svc = AsyncMock()
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/settings/",
                json={"home_layout": {"widgets": "not-a-list"}},
            )
        assert resp.status_code == 422
    finally:
        _clear_overrides(test_app)
