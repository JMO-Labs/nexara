"""
@file test_branding_presets.py
@brief Unit tests for branding preset themes (load, validate, apply).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import NotFoundError
from app.schemas.branding import PresetTheme
from app.services.branding.contrast import contrast_ratio
from app.services.branding_service import BrandingService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
EXPECTED = {"Ocean", "Forest", "Sunset", "Midnight", "Rose", "Lavender", "Coral", "Slate"}


def _service() -> tuple[BrandingService, AsyncMock]:
    repo = AsyncMock()

    async def upsert(_cid, values):
        defaults = {
            "id": uuid.uuid4(),
            "community_name": "Nexara",
            "tagline": None,
            "font_family": "Inter",
            "font_family_mono": "JetBrains Mono",
            "email_logo_media_id": None,
            "email_footer_text": None,
            "email_sender_name": None,
            "landing_cta_text": "Join our community",
            "landing_show_feature_list": True,
            "pwa_icon_192_media_id": None,
            "pwa_icon_512_media_id": None,
            "about_short": None,
            "custom_css": None,
            "custom_css_enabled": False,
        }
        return SimpleNamespace(**{**defaults, **values})

    repo.upsert.side_effect = upsert
    return BrandingService(repo=repo, community_id=COMMUNITY_ID), repo


class TestGetPresetThemes:
    async def test_loads_all_named_themes(self):
        service, _ = _service()
        themes = await service.get_preset_themes()
        assert all(isinstance(t, PresetTheme) for t in themes)
        assert EXPECTED <= {t.name for t in themes}
        assert len(themes) >= 8

    async def test_contrast_passes_aa_for_all_themes(self):
        service, _ = _service()
        for t in await service.get_preset_themes():
            assert contrast_ratio(t.text_light, t.surface_light) >= 4.5, t.name
            assert contrast_ratio(t.text_dark, t.surface_dark) >= 4.5, t.name
            assert contrast_ratio("#14301E", t.accent) >= 4.5, t.name
            assert contrast_ratio("#ffffff", t.primary) >= 3.0, t.name
            assert contrast_ratio(t.text_dark, t.primary_dark) >= 4.5, t.name


class TestApplyPresetTheme:
    async def test_applies_all_colors(self):
        service, repo = _service()
        user_id = uuid.uuid4()
        result = await service.apply_preset_theme("Ocean", user_id=user_id)
        values = repo.upsert.await_args.args[1]
        assert values["color_primary"] == "#0284c7"
        assert set(values) >= {
            "color_primary", "color_primary_dark", "color_accent",
            "color_surface_light", "color_surface_dark",
            "color_text_light", "color_text_dark",
        }  # fmt: skip
        assert result.branding.color_primary == "#0284c7"

    async def test_name_is_case_insensitive(self):
        service, repo = _service()
        await service.apply_preset_theme("forest", user_id=uuid.uuid4())
        repo.upsert.assert_awaited_once()

    async def test_unknown_theme_raises_not_found(self):
        service, repo = _service()
        with pytest.raises(NotFoundError):
            await service.apply_preset_theme("Nope", user_id=uuid.uuid4())
        repo.upsert.assert_not_awaited()
