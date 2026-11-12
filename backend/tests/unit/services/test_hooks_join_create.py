"""
@file test_hooks_join_create.py
@brief on_user_joined / on_community_created hook emission (nexara#304).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.plugins.hooks import HookRegistry
from app.plugins.manifest import PluginManifest
from app.services.community_service import CommunityService
from tests.unit.services.test_auth_service import _make_service, _make_user


@pytest.fixture(autouse=True)
def _clean_registry():
    HookRegistry.reset()
    with patch("app.services.auth.sso_only.is_sso_only", AsyncMock(return_value=False)):
        yield
    HookRegistry.reset()


def _register_failing(event: str, community_id: uuid.UUID) -> None:
    """@brief Register a plugin handler that always raises."""
    manifest = PluginManifest(
        id="bad",
        name="Bad",
        version="1.0.0",
        author="t",
        description="t",
        min_core_version="1.0.0",
        hooks={event: "boom"},
        permissions=[f"hooks_{event}"],
    )

    async def boom(ctx, **kw):
        raise RuntimeError("boom")

    HookRegistry.register(community_id, event, "bad", boom, manifest)


async def test_register_emits_on_user_joined():
    svc = _make_service()
    svc._user_repo.email_exists.return_value = False
    svc._user_repo.username_exists.return_value = False
    created = _make_user()
    svc._user_repo.create.return_value = created
    with patch("app.services.auth_service.HookRegistry.emit", new=AsyncMock()) as emit:
        await svc.register(
            email="n@example.com", username="n", password="strong-password123", display_name="N"
        )
    emit.assert_awaited_once_with(
        "on_user_joined",
        community_id=created.community_id,
        session=svc._session,
        user_id=created.id,
    )


async def test_register_survives_hook_failure():
    svc = _make_service()
    svc._user_repo.email_exists.return_value = False
    svc._user_repo.username_exists.return_value = False
    svc._user_repo.create.return_value = _make_user()
    _register_failing("on_user_joined", svc._user_repo.create.return_value.community_id)
    result = await svc.register(
        email="n@example.com", username="n", password="strong-password123", display_name="N"
    )
    assert result["access_token"]


async def test_create_community_emits_on_community_created():
    session = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    owner = uuid.uuid4()
    cid = uuid.uuid4()

    def _add(obj):
        obj.id = cid

    session.add.side_effect = _add
    with patch("app.services.community_service.HookRegistry.emit", new=AsyncMock()) as emit:
        community = await CommunityService(session).create_community("Club", owner)
    assert community.id == cid
    emit.assert_awaited_once_with(
        "on_community_created", community_id=cid, session=session, user_id=owner
    )


async def test_create_community_survives_hook_failure():
    session = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    cid = uuid.uuid4()
    session.add.side_effect = lambda o: setattr(o, "id", cid)
    _register_failing("on_community_created", cid)
    community = await CommunityService(session).create_community("Club", uuid.uuid4())
    assert community.name == "Club"
