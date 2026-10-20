"use client";
/**
 * @file components/layout/BrandingStyle.tsx
 * @brief Applies community branding at runtime: sets --nx-accent on <html>
 *        and publishes name/logo to the branding store. Renders nothing.
 */
import { useEffect } from "react";
import { useBranding } from "@/hooks/useBranding";
import { accentPassesAA } from "@/lib/api/branding";
import { useBrandingStore } from "@/stores/branding";

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
    if (accentPassesAA(data.color_accent)) {
      root.style.setProperty("--nx-accent", data.color_accent);
    } else {
      root.style.removeProperty("--nx-accent");
    }
    setBrand(data.community_name, data.logo_light_url);
    return () => {
      root.style.removeProperty("--nx-accent");
    };
  }, [data, setBrand]);

  return null;
}
