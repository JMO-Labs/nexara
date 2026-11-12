/**
 * @file lib/api/branding.ts
 * @brief Branding API (GET public, PUT admin) plus accent-contrast check.
 */
import { apiGet, apiPut } from "./client";
import { contrastRatio } from "@/lib/contrast";
import { palette } from "@/theme/palette";

const BASE = "/api/v1/branding/";

export interface Branding {
  community_name: string;
  tagline: string | null;
  color_accent: string;
  color_primary?: string;
  color_primary_dark?: string;
  color_surface_light?: string;
  color_surface_dark?: string;
  color_text_light?: string;
  color_text_dark?: string;
  font_family?: string;
  font_family_mono?: string;
  logo_light_url: string | null;
  logo_dark_url: string | null;
  email_logo_media_id?: string | null;
  email_footer_text?: string | null;
  email_sender_name?: string | null;
  landing_cta_text?: string | null;
  landing_show_feature_list?: boolean;
  pwa_icon_192_media_id?: string | null;
  pwa_icon_512_media_id?: string | null;
}

export interface BrandingUpdate {
  community_name?: string;
  tagline?: string;
  color_accent?: string;
  color_primary?: string;
  color_primary_dark?: string;
  color_surface_light?: string;
  color_surface_dark?: string;
  color_text_light?: string;
  color_text_dark?: string;
  font_family?: string;
  font_family_mono?: string;
  email_logo_media_id?: string;
  email_footer_text?: string;
  email_sender_name?: string;
  landing_cta_text?: string;
  landing_show_feature_list?: boolean;
  pwa_icon_192_media_id?: string;
  pwa_icon_512_media_id?: string;
}

/** @brief Fetch current branding (public). */
export const getBranding = () => apiGet<Branding>(BASE);

/**
 * @brief Update branding (admin only).
 * @param body fields to change
 * @return updated branding wrapped with contrast warnings
 */
export const updateBranding = (body: BrandingUpdate) =>
  apiPut<{ branding: Branding }>(BASE, body);

/**
 * @brief Whether forest text on this accent meets WCAG AA (4.5:1).
 * @param accent #RRGGBB color
 * @return true if accent is a valid hex and passes
 */
export function accentPassesAA(accent: string): boolean {
  if (!/^#[0-9a-fA-F]{6}$/.test(accent)) return false;
  return contrastRatio(palette.light["surface-strong"], accent) >= 4.5;
}

/** @brief True if value is a #RRGGBB hex color. */
export const isHex = (v: unknown): v is string =>
  typeof v === "string" && /^#[0-9a-fA-F]{6}$/.test(v);

/** @brief True if value is a safe font family name (letters, digits, space, dash). */
export const isFontName = (v: unknown): v is string =>
  typeof v === "string" && /^[A-Za-z0-9][A-Za-z0-9 \-]{0,63}$/.test(v);
