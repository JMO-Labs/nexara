/**
 * @file lib/brandingVars.ts
 * @brief Map saved branding to validated CSS custom properties.
 */
import type { Branding } from "@/lib/api/branding";
import { accentPassesAA, isFontName, isHex } from "@/lib/api/branding";

/** @brief Every property BrandingStyle may set on <html>. */
export const BRANDING_VARS = [
  "--nx-accent",
  "--nx-surface",
  "--nx-ink",
  "--nx-surface-strong",
  "--font-sans",
  "--font-mono",
] as const;

export type BrandingVar = (typeof BRANDING_VARS)[number];

const SANS_FALLBACK = "var(--font-hanken), system-ui, sans-serif";
const MONO_FALLBACK = "ui-monospace, monospace";

const hex = (v: unknown): string | null => (isHex(v) ? v : null);
const font = (v: unknown, fallback: string): string | null =>
  isFontName(v) ? `"${v}", ${fallback}` : null;

/**
 * @brief Compute CSS vars for the given branding and theme mode.
 * @param b branding data
 * @param dark whether dark mode is active
 * @return map of var -> value; null means remove (globals.css default)
 */
export function brandingVars(
  b: Branding,
  dark: boolean,
): Record<BrandingVar, string | null> {
  return {
    "--nx-accent": accentPassesAA(b.color_accent) ? b.color_accent : null,
    "--nx-surface": hex(dark ? b.color_surface_dark : b.color_surface_light),
    "--nx-ink": hex(dark ? b.color_text_dark : b.color_text_light),
    "--nx-surface-strong": hex(dark ? b.color_primary_dark : b.color_primary),
    "--font-sans": font(b.font_family, SANS_FALLBACK),
    "--font-mono": font(b.font_family_mono, MONO_FALLBACK),
  };
}
