"""
@file
@brief Plugin scope allowlist against the REAL app router tree (prefixes included).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_db
from app.models.user import COMMUNITY_DEFAULT
from app.plugins.scopes import PLUGIN_ROUTE_SCOPES

CID = uuid.UUID(COMMUNITY_DEFAULT)
TOK = "nxp_" + "b" * 40
ALL = sorted(set(PLUGIN_ROUTE_SCOPES.values()))
SAMPLE = {
    "{post_id}": str(uuid.uuid4()),
    "{comment_id}": str(uuid.uuid4()),
    "{media_id}": str(uuid.uuid4()),
    "{user_id}": str(uuid.uuid4()),
}


def _concrete(t: str) -> str:
    for k, v in SAMPLE.items():
        t = t.replace(k, v)
    return t


@pytest.fixture
def real_app(test_app):
    bot = SimpleNamespace(id=uuid.uuid4(), community_id=CID, is_bot=True)
    db = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = bot
    db.execute.return_value = res

    async def _db():
        yield db

    test_app.dependency_overrides[get_db] = _db
    return test_app


async def _call(app, method, path, scopes):
    row = (
        SimpleNamespace(id=uuid.uuid4(), community_id=CID),
        SimpleNamespace(id=uuid.uuid4(), granted_scopes=scopes),
        SimpleNamespace(bot_user_id=uuid.uuid4()),
    )
    with patch(
        "app.repositories.plugin_repo.PluginRepository.resolve_token",
        AsyncMock(return_value=row),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            return await c.request(
                method, path, headers={"Authorization": f"Bearer {TOK}"}, content=b"{}"
            )


@pytest.mark.parametrize(("method", "template"), sorted(PLUGIN_ROUTE_SCOPES))
async def test_allowlisted_route_passes_scope_gate(real_app, method, template) -> None:
    r = await _call(real_app, method, _concrete(template), ALL)
    assert not (r.status_code == 403 and r.json()["error"]["code"] == "plugin_scope_denied")
    assert r.status_code != 401


@pytest.mark.parametrize(("method", "template"), sorted(PLUGIN_ROUTE_SCOPES))
async def test_allowlisted_route_denied_without_scope(real_app, method, template) -> None:
    r = await _call(real_app, method, _concrete(template), [])
    assert r.status_code == 403 and r.json()["error"]["code"] == "plugin_scope_denied"


async def test_non_allowlisted_routes_denied(real_app) -> None:
    for method, path in (
        ("GET", "/api/v1/users"),
        ("GET", "/api/v1/admin/users"),
        ("DELETE", f"/api/v1/posts/{uuid.uuid4()}"),
    ):
        r = await _call(real_app, method, path, ALL)
        assert r.status_code == 403, path
        assert r.json()["error"]["code"] == "plugin_scope_denied", path


async def test_lookup_not_confused_with_user_id(real_app) -> None:
    r = await _call(real_app, "GET", "/api/v1/users/lookup?username=x", ["users:read"])
    assert r.status_code != 403


async def test_media_file_nxp_token_not_anonymous(real_app) -> None:
    r = await _call(real_app, "GET", f"/api/v1/media/{uuid.uuid4()}/file", [])
    assert r.status_code == 403 and r.json()["error"]["code"] == "plugin_scope_denied"


async def test_rotating_fake_nxp_tokens_share_ip_bucket(real_app) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=real_app, raise_app_exceptions=False), base_url="http://t"
    ) as c:
        codes = []
        for i in range(15):
            r = await c.post(
                "/api/v1/auth/2fa/login",
                headers={"Authorization": f"Bearer nxp_fake{i}"},
                json={"two_factor_token": "x", "code": "123456"},
            )
            codes.append(r.status_code)
    assert 429 in codes and codes.index(429) <= 10


async def test_user_profile_shapes_human_vs_bot(real_app) -> None:
    from datetime import UTC, datetime
    from unittest.mock import patch as _patch

    from app.core.dependencies import get_current_user
    from app.schemas.profile import ProfileResponse

    full = ProfileResponse(
        id=uuid.uuid4(),
        username="u",
        display_name="U",
        role="member",
        created_at=datetime.now(UTC),
        pronouns="she/her",
    )
    human = SimpleNamespace(id=uuid.uuid4(), community_id=CID, is_bot=False)
    bot = SimpleNamespace(id=uuid.uuid4(), community_id=CID, is_bot=True)
    with (
        _patch("app.api.v1.users.ProfileService") as svc,
        _patch("app.api.v1.users.ProfileRepository"),
    ):
        svc.return_value.view = AsyncMock(return_value=full)
        async with AsyncClient(transport=ASGITransport(app=real_app), base_url="http://t") as c:
            real_app.dependency_overrides[get_current_user] = lambda: human
            h = (await c.get(f"/api/v1/users/{full.id}")).json()
            real_app.dependency_overrides[get_current_user] = lambda: bot
            b = (await c.get(f"/api/v1/users/{full.id}")).json()
    assert h["pronouns"] == "she/her" and "role" in h
    assert set(b) == {"id", "username", "display_name", "avatar_url"}
