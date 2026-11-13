"""
@file branding_service.py
@brief Business logic for community branding CRUD with Valkey caching.

Branding data is cached for 5 minutes in Valkey DB 2 and invalidated
on every admin update.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from redis.asyncio import Redis

from app.core.cache import DEFAULT_TTL, cache_delete, cache_get, cache_set
from app.core.exceptions import AppError, NotFoundError
from app.repositories.audit_repo import AuditRepository
from app.repositories.branding_repo import BrandingRepository
from app.schemas.branding import (
    BrandingResponse,
    BrandingUpdate,
    BrandingUpdateResponse,
    ContrastWarning,
    PresetTheme,
)
from app.services.branding.contrast import contrast_ratio
from app.services.branding.css import sanitize_css

if TYPE_CHECKING:
    from app.models.branding import CommunityBranding

logger = structlog.get_logger(__name__)

ALLOWED_FONTS = frozenset(
    {
        "Inter",
        "Roboto",
        "Open Sans",
        "Lato",
        "Poppins",
        "Montserrat",
        "Source Sans 3",
        "Noto Sans",
        "Raleway",
        "Ubuntu",
        "system-ui",
        "JetBrains Mono",
        "Fira Code",
        "Source Code Pro",
        "IBM Plex Mono",
    }
)


_PRESETS_PATH = Path(__file__).resolve().parents[2] / "data" / "preset_themes.json"
"""@brief Location of the bundled preset themes file."""


def _cache_key(community_id: uuid.UUID) -> str:
    """@brief Build the Valkey cache key for branding data."""
    return f"branding:{community_id}"


def _row_to_response(row: CommunityBranding) -> BrandingResponse:
    """@brief Build BrandingResponse from CommunityBranding row."""
    return BrandingResponse(
        community_name=row.community_name,
        tagline=row.tagline,
        color_primary=row.color_primary,
        color_primary_dark=row.color_primary_dark,
        logo_light_url=None,
        logo_dark_url=None,
        color_accent=getattr(row, "color_accent", "#C6B4F5"),
        color_surface_light=getattr(row, "color_surface_light", "#ffffff"),
        color_surface_dark=getattr(row, "color_surface_dark", "#1f2937"),
        color_text_light=getattr(row, "color_text_light", "#111827"),
        color_text_dark=getattr(row, "color_text_dark", "#f9fafb"),
        font_family=getattr(row, "font_family", "Inter"),
        font_family_mono=getattr(row, "font_family_mono", "JetBrains Mono"),
        email_logo_media_id=getattr(row, "email_logo_media_id", None),
        email_footer_text=getattr(row, "email_footer_text", None),
        email_sender_name=getattr(row, "email_sender_name", None),
        landing_cta_text=getattr(row, "landing_cta_text", "Join our community"),
        landing_show_feature_list=getattr(row, "landing_show_feature_list", True),
        pwa_icon_192_media_id=getattr(row, "pwa_icon_192_media_id", None),
        pwa_icon_512_media_id=getattr(row, "pwa_icon_512_media_id", None),
        about_short=getattr(row, "about_short", None),
        custom_css=getattr(row, "custom_css", None),
        custom_css_enabled=getattr(row, "custom_css_enabled", False),
    )


class BrandingService:
    """
    @brief Service layer for community branding operations.

    @param repo BrandingRepository instance.
    @param cache_client Async Redis client for Valkey DB 2 (or None).
    @param community_id UUID of the community scope.
    @param audit_repo Optional AuditRepository for logging admin actions.
    """

    def __init__(
        self,
        repo: BrandingRepository,
        cache_client: Redis | None = None,
        community_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001"),
        audit_repo: AuditRepository | None = None,
    ) -> None:
        self._repo = repo
        self._cache = cache_client
        self._community_id = community_id
        self._audit = audit_repo

    async def get_branding(self) -> BrandingResponse:
        """
        @brief Return branding data, serving from cache when available.

        Cache-aside pattern: check Valkey first, fall through to Postgres
        on miss, then write back to cache.

        @return BrandingResponse with current branding values.
        """
        key = _cache_key(self._community_id)

        if self._cache is not None:
            cached = await cache_get(self._cache, key)
            if cached is not None:
                data = json.loads(cached)
                return BrandingResponse(**data)

        row = await self._repo.get(self._community_id)
        if row is None:
            response = BrandingResponse(
                community_name="Nexara",
                color_primary="#3b82f6",
                color_primary_dark="#2563eb",
            )
        else:
            response = _row_to_response(row)

        if self._cache is not None:
            await cache_set(self._cache, key, response.model_dump_json(), DEFAULT_TTL)

        return response

    async def update_branding(
        self,
        *,
        user_id: uuid.UUID,
        data: BrandingUpdate,
        ip_address: str | None = None,
    ) -> BrandingUpdateResponse:
        """
        @brief Update branding, invalidate cache, and write an audit entry.

        @param user_id UUID of the admin performing the update.
        @param data Validated branding update payload.
        @param ip_address Request originator IP for audit log.
        @return Updated BrandingResponse.
        """
        update_dict = data.model_dump(exclude_none=True)
        if data.custom_css is not None:
            update_dict["custom_css"] = self._sanitize(data.custom_css)
        update_dict["updated_by"] = user_id

        row = await self._repo.upsert(self._community_id, update_dict)

        key = _cache_key(self._community_id)
        if self._cache is not None:
            await cache_delete(self._cache, key)

        if self._audit is not None:
            await self._audit.append(
                actor_id=user_id,
                action="branding.updated",
                target_type="branding",
                target_id=row.id,
                extra_data={"fields": list(update_dict.keys())},
                ip_address=ip_address,
            )

        logger.info("branding_updated", user_id=str(user_id), fields=list(update_dict.keys()))

        response = _row_to_response(row)
        warnings = self.check_contrast(row)
        return BrandingUpdateResponse(branding=response, contrast_warnings=warnings)

    async def get_preset_themes(self) -> list[PresetTheme]:
        """
        @brief Load preset themes from the bundled JSON file.

        @return List of PresetTheme.
        """
        raw = json.loads(_PRESETS_PATH.read_text(encoding="utf-8"))
        return [PresetTheme(**t) for t in raw["themes"]]

    async def apply_preset_theme(
        self,
        theme_name: str,
        *,
        user_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> BrandingUpdateResponse:
        """
        @brief Apply a preset theme's colours via update_branding().

        @param theme_name Theme name (case-insensitive).
        @param user_id Admin applying the theme.
        @param ip_address Request IP for the audit log.
        @return Updated branding with contrast warnings.
        @throws NotFoundError if no theme has that name.
        """
        wanted = theme_name.strip().lower()
        theme = next((t for t in await self.get_preset_themes() if t.name.lower() == wanted), None)
        if theme is None:
            raise NotFoundError(f"Preset theme not found: {theme_name}")
        data = BrandingUpdate(
            color_primary=theme.primary,
            color_primary_dark=theme.primary_dark,
            color_accent=theme.accent,
            color_surface_light=theme.surface_light,
            color_surface_dark=theme.surface_dark,
            color_text_light=theme.text_light,
            color_text_dark=theme.text_dark,
        )
        return await self.update_branding(user_id=user_id, data=data, ip_address=ip_address)

    @staticmethod
    def _sanitize(raw: str) -> str:
        """@brief Sanitize CSS; reject if over half of it was removed."""
        clean = sanitize_css(raw)
        if len(clean.encode("utf-8")) * 2 < len(raw.encode("utf-8")):
            raise AppError(
                code="css_invalid",
                message="Custom CSS contains too many disallowed constructs",
                status_code=400,
            )
        return clean

    def check_contrast(self, branding: CommunityBranding) -> list[ContrastWarning]:
        """
        @brief Check text vs background contrast for light and dark modes.

        WCAG AA = 4.5:1 normal text, 3:1 large text.
        @return List of ContrastWarning for pairs that fail AA.
        """
        warnings: list[ContrastWarning] = []
        aa_min = 4.5
        aaa_min = 7.0

        pairs = [
            (branding.color_text_light, branding.color_surface_light),
            (branding.color_text_dark, branding.color_surface_dark),
        ]
        for text_color, bg_color in pairs:
            try:
                ratio = contrast_ratio(text_color, bg_color)
                passes_aa = ratio >= aa_min
                passes_aaa = ratio >= aaa_min
                if not passes_aa:
                    warnings.append(
                        ContrastWarning(
                            color1=text_color,
                            color2=bg_color,
                            ratio=round(ratio, 2),
                            passes_aa=passes_aa,
                            passes_aaa=passes_aaa,
                        )
                    )
            except (ValueError, AttributeError):
                pass
        return warnings

    def generate_pwa_manifest(
        self, branding: BrandingResponse | CommunityBranding, base_url: str = ""
    ) -> dict[str, Any]:
        """
        @brief Generate PWA manifest from branding data.

        @param branding CommunityBranding row or mock.
        @param base_url APP_BASE_URL for start_url and icon URLs.
        @return Dict suitable for manifest.json.
        """
        name = getattr(branding, "community_name", "Nexara")
        short_name = name[:12] if len(name) > 12 else name
        theme_color = getattr(branding, "color_primary", "#3b82f6")
        bg_color = getattr(branding, "color_surface_light", "#ffffff")
        start_url = f"{base_url.rstrip('/')}/" if base_url else "/"

        icons: list[dict[str, Any]] = []
        icon_192 = getattr(branding, "pwa_icon_192_media_id", None)
        icon_512 = getattr(branding, "pwa_icon_512_media_id", None)
        if icon_192:
            icons.append(
                {
                    "src": f"{base_url}/api/v1/media/{icon_192}",
                    "sizes": "192x192",
                    "type": "image/png",
                }
            )
        if icon_512:
            icons.append(
                {
                    "src": f"{base_url}/api/v1/media/{icon_512}",
                    "sizes": "512x512",
                    "type": "image/png",
                }
            )
        if not icons:
            icons.append({"src": "/favicon.ico", "sizes": "any", "type": "image/x-icon"})

        return {
            "name": name,
            "short_name": short_name,
            "theme_color": theme_color,
            "background_color": bg_color,
            "display": "standalone",
            "start_url": start_url,
            "icons": icons,
        }

    def validate_font_family(self, font: str) -> bool:
        """@brief Validate font against allowed list."""
        return font.strip() in ALLOWED_FONTS
