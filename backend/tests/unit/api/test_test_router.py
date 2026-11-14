"""
@file test_test_router.py
@brief The test-only notify router is mounted only when APP_ENV == "test".
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings


async def _post(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        return await c.post(
            "/api/v1/_test/notify",
            json={"type": "system", "payload": {"message": "hi", "link": "/app"}},
        )


@pytest.mark.asyncio
async def test_absent_outside_test_env(test_app):
    assert (await _post(test_app)).status_code == 404


@pytest.mark.asyncio
async def test_mounted_in_test_env_and_notifies(test_app):
    from app.api.v1 import _test as mod
    from app.core.dependencies import get_current_user, get_db

    settings = get_settings().model_copy(update={"APP_ENV": "test"})

    with patch("app.main.get_settings", lambda: settings):
        from app.main import create_app

        app = create_app()
    user = MagicMock()
    user.id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    svc = MagicMock()
    svc.notify = AsyncMock(return_value=MagicMock(id=uuid.uuid4()))
    app.dependency_overrides[mod.get_notification_service] = lambda: svc

    resp = await _post(app)
    assert resp.status_code == 201
    svc.notify.assert_awaited_once()
    assert svc.notify.await_args.args[0] == user.id
    assert svc.notify.await_args.args[1] == "system"
