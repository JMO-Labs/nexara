"""
@file test_branding_full.py
@brief Unit tests for branding full palette features.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.branding.contrast import contrast_ratio, relative_luminance


class TestContrastRatio:
    def test_black_white_max_contrast(self):
        ratio = contrast_ratio("#000000", "#ffffff")
        assert ratio == pytest.approx(21.0, rel=0.01)

    def test_same_color_min_contrast(self):
        ratio = contrast_ratio("#ff0000", "#ff0000")
        assert ratio == pytest.approx(1.0, rel=0.01)

    def test_warns_low_contrast(self):
        ratio = contrast_ratio("#777777", "#888888")
        assert ratio < 4.5  # Fails AA

    def test_passes_good_contrast(self):
        ratio = contrast_ratio("#000000", "#ffffff")
        assert ratio >= 4.5  # Passes AA


class TestRelativeLuminance:
    def test_black_luminance(self):
        assert relative_luminance("#000000") == pytest.approx(0.0, abs=0.001)

    def test_white_luminance(self):
        assert relative_luminance("#ffffff") == pytest.approx(1.0, abs=0.001)


class TestBrandingServiceContrast:
    def test_check_contrast_returns_warnings(self):
        from app.services.branding_service import BrandingService

        branding = MagicMock()
        branding.color_text_light = "#777777"
        branding.color_surface_light = "#888888"
        branding.color_text_dark = "#f9fafb"
        branding.color_surface_dark = "#1f2937"

        service = BrandingService(repo=AsyncMock(), cache_client=None, community_id=MagicMock())
        warnings = service.check_contrast(branding)

        low_warnings = [w for w in warnings if not w.passes_aa]
        assert len(low_warnings) >= 1


class TestPwaManifest:
    def test_pwa_manifest_generated(self):
        from app.services.branding_service import BrandingService

        branding = MagicMock()
        branding.community_name = "Test Community"
        branding.color_primary = "#3b82f6"
        branding.color_surface_light = "#ffffff"
        branding.pwa_icon_192_media_id = None
        branding.pwa_icon_512_media_id = None

        service = BrandingService(repo=AsyncMock(), cache_client=None, community_id=MagicMock())
        manifest = service.generate_pwa_manifest(branding)

        assert manifest["name"] == "Test Community"
        assert manifest["theme_color"] == "#3b82f6"
        assert manifest["display"] == "standalone"


class TestFontValidation:
    def test_valid_font_accepted(self):
        from app.services.branding_service import BrandingService

        service = BrandingService(repo=AsyncMock(), cache_client=None, community_id=MagicMock())
        assert service.validate_font_family("Inter") is True

    def test_invalid_font_rejected(self):
        from app.services.branding_service import BrandingService

        service = BrandingService(repo=AsyncMock(), cache_client=None, community_id=MagicMock())
        assert service.validate_font_family("Comic Sans MS") is False


class TestPwaManifestVersion:
    def _service(self):
        from app.services.branding_service import BrandingService

        return BrandingService(repo=AsyncMock(), cache_client=None, community_id=MagicMock())

    def _branding(self, name="Test", icon=None):
        b = MagicMock()
        b.community_name = name
        b.color_primary = "#3b82f6"
        b.color_surface_light = "#ffffff"
        b.pwa_icon_192_media_id = icon
        b.pwa_icon_512_media_id = None
        return b

    def test_version_present_and_stable(self):
        s = self._service()
        m1 = s.generate_pwa_manifest(self._branding())
        m2 = s.generate_pwa_manifest(self._branding())
        assert m1["version"] == m2["version"]

    def test_version_changes_when_icon_or_name_changes(self):
        s = self._service()
        base = s.generate_pwa_manifest(self._branding())["version"]
        assert s.generate_pwa_manifest(self._branding(name="Other"))["version"] != base
        icon = "11111111-1111-1111-1111-111111111111"
        assert s.generate_pwa_manifest(self._branding(icon=icon))["version"] != base
