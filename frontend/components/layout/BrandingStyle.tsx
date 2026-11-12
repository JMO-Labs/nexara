"use client";
/**
 * @file components/layout/BrandingStyle.tsx
 * @brief Applies community branding at runtime: palette + fonts as CSS vars
 *        on <html> (dark values via a scoped .dark style element) and
 *        publishes name/logo to the branding store. Renders nothing.
 */
import { useEffect } from "react";
import { useBranding } from "@/hooks/useBranding";
import { accentPassesAA, isFontName, isHex } from "@/lib/api/branding";
import type { Branding } from "@/lib/api/branding";
import { useBrandingStore } from "@/stores/branding";

const STYLE_ID = "nx-branding-dark";
const SANS_FALLBACK = "system-ui, sans-serif";
const MONO_FALLBACK = "ui-monospace, monospace";

/** @brief Light-mode CSS var map; only valid values are included. */
function lightVars(d: Branding): Record<string, string> {
  const v: Record<string, string> = {};
  if (accentPassesAA(d.color_accent)) v["--nx-accent"] = d.color_accent;
  if (isHex(d.color_surface_light)) v["--nx-surface"] = d.color_surface_light;
  if (isHex(d.color_text_light)) v["--nx-ink"] = d.color_text_light;
  if (isHex(d.color_primary)) v["--nx-surface-strong"] = d.color_primary;
  if (isFontName(d.font_family))
    v["--font-sans"] = `"${d.font_family}", ${SANS_FALLBACK}`;
  if (isFontName(d.font_family_mono))
    v["--font-mono"] = `"${d.font_family_mono}", ${MONO_FALLBACK}`;
  return v;
}

/** @brief Dark-mode CSS var map; only valid values are included. */
function darkVars(d: Branding): Record<string, string> {
  const v: Record<string, string> = {};
  if (isHex(d.color_surface_dark)) v["--nx-surface"] = d.color_surface_dark;
  if (isHex(d.color_text_dark)) v["--nx-ink"] = d.color_text_dark;
  if (isHex(d.color_primary_dark))
    v["--nx-surface-strong"] = d.color_primary_dark;
  return v;
}

/**
 * @brief Branding side-effect component.
 * @return null
 */
export function BrandingStyle() {
  const { data } = useBranding();
  const setBrand = useBrandingStore((s) => s.set);

  useEffect(() => {
    if (!data) return;
    const root = document.documentElement;
    const light = lightVars(data);
    for (const [k, val] of Object.entries(light))
      root.style.setProperty(k, val);

    const dark = Object.entries(darkVars(data))
      .map(([k, val]) => `${k}:${val}`)
      .join(";");
    const el = document.createElement("style");
    el.id = STYLE_ID;
    el.textContent = `.dark{${dark}}`;
    document.head.appendChild(el);

    setBrand(data.community_name, data.logo_light_url);
    return () => {
      for (const k of Object.keys(light)) root.style.removeProperty(k);
      el.remove();
    };
  }, [data, setBrand]);

  return null;
}
