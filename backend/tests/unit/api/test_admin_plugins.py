"""
@file test_admin_plugins.py
@brief Unit tests for admin plugin API-key endpoints.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

BASE = "/api/v1/admin/plugins/hello/api-keys"


def _key(revoked: bool = False) -> MagicMock:
    k = MagicMock()
    k.id = uuid.uuid4()
    k.plugin_id = "hello"
    k.key_hint = "abcd"
    k.created_at = datetime.now(UTC)
    k.last_used_at = None
    k.revoked_at = datetime.now(UTC) if revoked else None
    return k


@pytest.fixture
def admin_override(test_app):
    from app.core.dependencies import get_current_user

    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = "admin"

    async def _override():
        return user

    test_app.dependency_overrides[get_current_user] = _override
    yield user
    test_app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def repos():
    with (
        patch("app.api.v1.admin_plugins.PluginApiKeyRepository") as keys_cls,
        patch("app.api.v1.admin_plugins.AuditRepository") as audit_cls,
    ):
        keys, audit = AsyncMock(), AsyncMock()
        keys.plugin_exists = AsyncMock(return_value=True)
        keys_cls.return_value, audit_cls.return_value = keys, audit
        yield keys, audit


async def _call(test_app, method: str, url: str):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        return await c.request(method, url)


@pytest.mark.asyncio
async def test_create_returns_plaintext_once_and_audits(test_app, admin_override, repos):
    keys, audit = repos
    keys.create = AsyncMock(return_value=_key())
    resp = await _call(test_app, "POST", BASE)
    assert resp.status_code == 201
    body = resp.json()
    assert body["key"].startswith("nxr_plugin_hello_")
    stored_hash = keys.create.call_args.kwargs["key_hash"]
    assert stored_hash != body["key"]
    assert audit.append.call_args.kwargs["action"] == "plugin_api_key.created"
    assert body["key"] not in str(audit.append.call_args)


@pytest.mark.asyncio
async def test_create_unknown_plugin_404(test_app, admin_override, repos):
    repos[0].plugin_exists = AsyncMock(return_value=False)
    assert (await _call(test_app, "POST", BASE)).status_code == 404


@pytest.mark.asyncio
async def test_list_is_masked(test_app, admin_override, repos):
    repos[0].list_for_plugin = AsyncMock(return_value=[_key()])
    resp = await _call(test_app, "GET", BASE)
    assert resp.status_code == 200
    item = resp.json()[0]
    assert item["masked_key"] == "nxr_plugin_hello_" + "*" * 28 + "abcd"
    assert "key" not in item and "key_hash" not in item


@pytest.mark.asyncio
async def test_revoke_audits(test_app, admin_override, repos):
    keys, audit = repos
    key = _key()
    keys.get = AsyncMock(return_value=key)
    keys.revoke = AsyncMock(return_value=_key(revoked=True))
    resp = await _call(test_app, "DELETE", f"{BASE}/{key.id}")
    assert resp.status_code == 200
    assert audit.append.call_args.kwargs["action"] == "plugin_api_key.revoked"


@pytest.mark.asyncio
async def test_revoke_missing_404(test_app, admin_override, repos):
    repos[0].get = AsyncMock(return_value=None)
    assert (await _call(test_app, "DELETE", f"{BASE}/{uuid.uuid4()}")).status_code == 404


@pytest.mark.asyncio
async def test_requires_admin(test_app, repos):
    assert (await _call(test_app, "GET", BASE)).status_code == 401
