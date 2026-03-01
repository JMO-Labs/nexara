/**
 * @file composables/useBranding.ts
 * @brief Fetches community branding and injects CSS custom properties.
 *
 * On app init the composable calls GET /api/v1/branding/ (public, no auth)
 * and sets CSS custom properties on :root so Tailwind and components can
 * reference branding colors.  Re-fetch is triggered when the admin saves
 * branding changes.
 */

import { ref, readonly } from "vue";

/** @brief Shape of the branding data from the API. */
export interface BrandingData {
  community_name: string;
  tagline: string | null;
  color_primary: string;
  color_primary_dark: string;
  logo_light_url: string | null;
  logo_dark_url: string | null;
}

/** @brief Default branding values before API response. */
const DEFAULT_BRANDING: BrandingData = {
  community_name: "Nexara",
  tagline: null,
  color_primary: "#3b82f6",
  color_primary_dark: "#2563eb",
  logo_light_url: null,
  logo_dark_url: null,
};

const branding = ref<BrandingData>({ ...DEFAULT_BRANDING });
const loaded = ref(false);

/**
 * @brief Convert hex color to HSL values for Tailwind (format: "H S% L%").
 * @param hex - Hex color string (e.g. "#3b82f6" or "3b82f6").
 * @returns HSL string suitable for CSS var, e.g. "221 83% 53%".
 */
function hexToHsl(hex: string): string {
  const clean = hex.replace(/^#/, "");
  const r = parseInt(clean.slice(0, 2), 16) / 255;
  const g = parseInt(clean.slice(2, 4), 16) / 255;
  const b = parseInt(clean.slice(4, 6), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    switch (max) {
      case r:
        h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
        break;
      case g:
        h = ((b - r) / d + 2) / 6;
        break;
      case b:
        h = ((r - g) / d + 4) / 6;
        break;
    }
  }

  const s = l === 0 || l === 1 ? 0 : (max - min) / (1 - Math.abs(2 * l - 1));
  const hDeg = Math.round(h * 360);
  const sPct = Math.round(s * 100);
  const lPct = Math.round(l * 100);

  return `${hDeg} ${sPct}% ${lPct}%`;
}

/**
 * @brief Apply branding colors as CSS custom properties on :root.
 * Sets both hex vars (--color-primary) and HSL vars (--primary) for Tailwind.
 * @param data - Branding data to inject.
 */
function injectCssVariables(data: BrandingData): void {
  if (typeof document === "undefined") return;

  const root = document.documentElement;
  root.style.setProperty("--color-primary", data.color_primary);
  root.style.setProperty("--color-primary-dark", data.color_primary_dark);
  root.style.setProperty("--primary", hexToHsl(data.color_primary));
}

/**
 * @brief Composable for community branding data and CSS injection.
 * @returns branding ref, loaded flag, and fetchBranding/refresh functions.
 */
export function useBranding() {
  /**
   * @brief Fetch branding from the API and inject CSS variables.
   */
  async function fetchBranding(): Promise<void> {
    try {
      const response = await fetch("/api/v1/branding/");
      if (!response.ok) return;

      const data: BrandingData = await response.json();
      branding.value = data;
      injectCssVariables(data);
      loaded.value = true;
    } catch {
      branding.value = { ...DEFAULT_BRANDING };
      injectCssVariables(DEFAULT_BRANDING);
    }
  }

  return {
    branding: readonly(branding),
    loaded: readonly(loaded),
    fetchBranding,
  };
}
