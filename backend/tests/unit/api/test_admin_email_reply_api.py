"""
@file test_admin_email_reply_api.py
@brief /api/v1/admin/email-reply: admin only, validation, password never returned.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.dependencies import get_current_user, get_email_reply_admin_service
from app.services.email_reply_admin_service import EmailReplyAdminService
from tests.unit.services.email.test_reply_admin import COLS, FULL

URL = "/api/v1/admin/email-reply"


@pytest.fixture
def svc(test_app):
    row = SimpleNamespace(**COLS)

    async def update(_cid, values):
        for k, v in values.items():
            setattr(row, k, v)
        return row

    repo = AsyncMock()
    repo.get.return_value = row
    repo.update_inbound.side_effect = update
    s = EmailReplyAdminService(repo, uuid.uuid4(), Settings())
    test_app.dependency_overrides[get_email_reply_admin_service] = lambda: s
    yield s
    test_app.dependency_overrides.pop(get_email_reply_admin_service, None)
    test_app.dependency_overrides.pop(get_current_user, None)


def _login(test_app, role):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = role
    test_app.dependency_overrides[get_current_user] = lambda: user


async def _req(test_app, method, **kw):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        return await c.request(method, kw.pop("url", URL), **kw)


async def test_member_forbidden(test_app, svc):
    _login(test_app, "member")
    assert (await _req(test_app, "GET")).status_code == 403
    assert (await _req(test_app, "PUT", json=FULL)).status_code == 403
    assert (await _req(test_app, "POST", url=URL + "/test")).status_code == 403


async def test_put_then_get_never_returns_password(test_app, svc):
    _login(test_app, "admin")
    put = await _req(test_app, "PUT", json=FULL)
    assert put.status_code == 200 and put.json()["has_password"] is True
    got = await _req(test_app, "GET")
    assert "hunter2" not in got.text and "imap_password" not in got.json()
    assert got.json()["configured"] is True


async def test_validation_rejects_bad_address_and_port(test_app, svc):
    _login(test_app, "admin")
    assert (await _req(test_app, "PUT", json={"reply_address": "no-at"})).status_code == 422
    assert (await _req(test_app, "PUT", json={"imap_port": 0})).status_code == 422
    assert (await _req(test_app, "PUT", json={"imap_host": "a b"})).status_code == 422
