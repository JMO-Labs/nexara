"""
@file test_branding_presets_api.py
@brief Route-level tests for branding preset endpoints.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user, get_db
from app.schemas.branding import BrandingResponse, BrandingUpdateResponse


@pytest.fixture
def app(test_app: FastAPI) -> Iterator[FastAPI]:
    """@brief Test app with a mocked DB session."""

    async def _db() -> AsyncGenerator[MagicMock, None]:
        yield MagicMock()

    test_app.dependency_overrides[get_db] = _db
    yield test_app
    test_app.dependency_overrides.clear()


def _as(app: FastAPI, role: str) -> None:
    """@brief Authenticate requests as a user with the given role."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = role

    async def _user() -> MagicMock:
        return user

    app.dependency_overrides[get_current_user] = _user


def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def test_get_presets_is_public_and_returns_themes(app: FastAPI) -> None:
    async with _client(app) as c:
        resp = await c.get("/api/v1/branding/presets")
    assert resp.status_code == 200
    themes = resp.json()["themes"]
    assert len(themes) >= 6
    assert {"name", "primary", "accent"} <= themes[0].keys()


async def test_apply_preset_rejects_non_admin(app: FastAPI) -> None:
    _as(app, "member")
    with patch(
        "app.api.v1.branding.BrandingService.apply_preset_theme", new_callable=AsyncMock
    ) as apply:
        async with _client(app) as c:
            resp = await c.post("/api/v1/branding/presets/Forest/apply")
    assert resp.status_code == 403
    apply.assert_not_called()


async def test_apply_preset_calls_service_for_admin(app: FastAPI) -> None:
    _as(app, "admin")
    result = BrandingUpdateResponse(
        branding=BrandingResponse(
            community_name="C", color_primary="#000000", color_primary_dark="#111111"
        ),
        contrast_warnings=[],
    )
    with patch(
        "app.api.v1.branding.BrandingService.apply_preset_theme",
        new_callable=AsyncMock,
        return_value=result,
    ) as apply:
        async with _client(app) as c:
            resp = await c.post("/api/v1/branding/presets/Forest/apply")
    assert resp.status_code == 200
    assert resp.json()["branding"]["community_name"] == "C"
    assert apply.await_args.args[0] == "Forest"
