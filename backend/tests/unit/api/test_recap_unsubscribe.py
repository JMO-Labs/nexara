"""
@file test_recap_unsubscribe.py
@brief Unit tests for GET /recap/unsubscribe token handling.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, create_purpose_token


async def _get(test_app, token):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        return await c.get("/api/v1/recap/unsubscribe", params={"token": token})


async def test_bad_token_400(test_app):
    assert (await _get(test_app, "garbage")).status_code == 400


async def test_wrong_purpose_token_400(test_app):
    assert (await _get(test_app, create_access_token(uuid.uuid4()))).status_code == 400


async def test_expired_token_400(test_app):
    tok = create_purpose_token(uuid.uuid4(), "recap_unsub", timedelta(seconds=-5))
    assert (await _get(test_app, tok)).status_code == 400


async def test_good_token_sets_off(test_app):
    uid = uuid.uuid4()
    repo = MagicMock()
    repo.get_by_user_id = AsyncMock(return_value=MagicMock())
    repo.update = AsyncMock()
    with patch("app.api.v1.recap.SettingsRepository", return_value=repo):
        r = await _get(test_app, create_purpose_token(uid, "recap_unsub", timedelta(days=90)))
    assert r.status_code == 200
    assert "unsubscribed" in r.text
    repo.update.assert_awaited_once_with(uid, {"recap_cadence": "off"})
