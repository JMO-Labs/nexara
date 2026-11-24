"""
@file
@brief Plugin token auth: bot resolution, revocation, scope allowlist, rate limit, owner guard.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from slowapi import Limiter

from app.core.dependencies import get_current_user, get_db, require_instance_owner
from app.core.exceptions import AuthorizationError, register_exception_handlers
from app.models.user import COMMUNITY_DEFAULT
from app.services.age_service import is_adult

CID = uuid.UUID(COMMUNITY_DEFAULT)
TOK = "nxp_" + "a" * 40


def _bot(**kw):
    d = dict(id=uuid.uuid4(), community_id=CID, is_bot=True, role="member", age_group=None)
    d.update(kw)
    return SimpleNamespace(**d)


def _app(bot, row, limit: str | None = None) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    lim = Limiter(key_func=lambda r: "x", storage_uri="memory://")
    app.state.limiter = lim
    db = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = bot
    db.execute.return_value = res

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db

    @app.get("/api/v1/posts")
    async def posts(u=Depends(get_current_user)):
        return {"id": str(u.id)}

    @app.get("/api/v1/secret")
    async def secret(u=Depends(get_current_user)):
        return {}

    @app.get("/api/v1/media/{media_id}")
    async def media(media_id: str, u=Depends(get_current_user)):
        return {}

    app._row = row  # type: ignore[attr-defined]
    return app


def _row(scopes, community=CID, bot_id=None):
    tok = SimpleNamespace(id=uuid.uuid4(), community_id=community)
    inst = SimpleNamespace(id=uuid.uuid4(), granted_scopes=scopes)
    pc = SimpleNamespace(bot_user_id=bot_id or uuid.uuid4())
    return tok, inst, pc


async def _get(app, path, row, token=TOK):
    with patch(
        "app.repositories.plugin_repo.PluginRepository.resolve_token",
        AsyncMock(return_value=row),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            return await c.get(path, headers={"Authorization": f"Bearer {token}"})


async def test_valid_token_returns_bot() -> None:
    bot = _bot()
    r = await _get(_app(bot, None), "/api/v1/posts", _row(["posts:read"]))
    assert r.status_code == 200 and r.json()["id"] == str(bot.id)


async def test_revoked_token_401() -> None:
    r = await _get(_app(_bot(), None), "/api/v1/posts", None)
    assert r.status_code == 401


async def test_missing_or_inactive_bot_401() -> None:
    r = await _get(_app(None, None), "/api/v1/posts", _row(["posts:read"]))
    assert r.status_code == 401


async def test_unlisted_route_denied() -> None:
    r = await _get(_app(_bot(), None), "/api/v1/secret", _row(["posts:read", "posts:write"]))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "plugin_scope_denied"


async def test_scope_not_granted_denied() -> None:
    r = await _get(_app(_bot(), None), "/api/v1/posts", _row(["posts:write"]))
    assert r.status_code == 403 and r.json()["error"]["code"] == "plugin_scope_denied"


async def test_template_matching_not_concrete_path() -> None:
    r = await _get(_app(_bot(), None), "/api/v1/media/abc", _row(["media:read"]))
    assert r.status_code == 200


async def test_rate_limit_120_per_minute() -> None:
    app = _app(_bot(), None)
    row = _row(["posts:read"])
    codes = [(await _get(app, "/api/v1/posts", row)).status_code for _ in range(122)]
    assert codes[:120] == [200] * 120 and codes[120] == 429


async def test_jwt_path_unchanged() -> None:
    r = await _get(_app(_bot(), None), "/api/v1/posts", None, token="not.a.jwt")
    assert r.status_code == 401


def test_bot_never_adult() -> None:
    assert is_adult(SimpleNamespace(is_bot=True, age_group="adult", birthday=None), None) is False


async def test_instance_owner_guard() -> None:
    owner = SimpleNamespace(is_bot=False, role="admin", community_id=CID)
    assert await require_instance_owner(owner) is owner  # type: ignore[arg-type]
    for u in (
        SimpleNamespace(is_bot=False, role="admin", community_id=uuid.uuid4()),
        SimpleNamespace(is_bot=False, role="member", community_id=CID),
        SimpleNamespace(is_bot=True, role="admin", community_id=CID),
    ):
        with pytest.raises(AuthorizationError):
            await require_instance_owner(u)  # type: ignore[arg-type]
