"""
@file test_branding_presets.py
@brief Tests for preset branding themes: data validity, service, endpoints.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AppError
from app.repositories.branding_repo import BrandingRepository
from app.schemas.branding import PresetTheme
from app.services.branding.contrast import contrast_ratio
from app.services.branding_service import BrandingService

REQUIRED = {"Ocean", "Forest", "Sunset", "Midnight", "Rose", "Lavender", "Coral", "Slate"}


def _service() -> tuple[BrandingService, AsyncMock]:
    repo = AsyncMock(spec=BrandingRepository)
    return BrandingService(repo=repo), repo


class TestPresetData:
    async def test_loads_required_themes(self):
        svc, _ = _service()
        themes = await svc.get_preset_themes()
        assert REQUIRED <= {t.name for t in themes}
        assert all(isinstance(t, PresetTheme) for t in themes)

    async def test_contrast_passes_aa(self):
        svc, _ = _service()
        for t in await svc.get_preset_themes():
            assert contrast_ratio(t.text_light, t.surface_light) >= 4.5, t.name
            assert contrast_ratio(t.text_dark, t.surface_dark) >= 4.5, t.name
            assert contrast_ratio("#14301E", t.accent) >= 4.5, t.name
            assert contrast_ratio("#ffffff", t.primary) >= 4.5, t.name


class TestApplyPreset:
    async def test_applies_all_colors(self):
        svc, repo = _service()
        row = SimpleNamespace(id=uuid.uuid4(), community_name="X", tagline=None)
        theme = next(t for t in await svc.get_preset_themes() if t.name == "Ocean")
        for f in (
            "primary",
            "primary_dark",
            "accent",
            "surface_light",
            "surface_dark",
            "text_light",
            "text_dark",
        ):
            setattr(row, f"color_{f}", getattr(theme, f))
        repo.upsert.return_value = row
        res = await svc.apply_preset_theme("ocean", svc._community_id, user_id=uuid.uuid4())
        saved = repo.upsert.call_args.args[1]
        assert saved["color_primary"] == theme.primary
        assert saved["color_accent"] == theme.accent
        assert saved["color_text_dark"] == theme.text_dark
        assert res.branding.color_primary == theme.primary

    async def test_unknown_theme_404(self):
        svc, repo = _service()
        with pytest.raises(AppError) as exc:
            await svc.apply_preset_theme("nope", svc._community_id, user_id=uuid.uuid4())
        assert exc.value.status_code == 404
        repo.upsert.assert_not_called()


def test_routes_registered():
    from app.api.v1.branding import router

    paths = {r.path for r in router.routes}
    assert "/branding/presets" in paths
    assert "/branding/presets/{theme_name}/apply" in paths
