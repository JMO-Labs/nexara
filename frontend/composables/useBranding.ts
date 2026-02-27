/**
 * @file composables/useBranding.ts
 * @brief Fetches community branding and injects CSS custom properties.
 *
 * On app init the composable calls GET /api/v1/branding/ (public, no auth)
 * and sets CSS custom properties on :root so Tailwind and components can
 * reference branding colors.  Re-fetch is triggered when the admin saves
 * branding changes.
 */

import { ref, readonly } from 'vue'

/** @brief Shape of the branding data from the API. */
export interface BrandingData {
  community_name: string
  tagline: string | null
  color_primary: string
  color_primary_dark: string
  logo_light_url: string | null
  logo_dark_url: string | null
}

/** @brief Default branding values before API response. */
const DEFAULT_BRANDING: BrandingData = {
  community_name: 'Nexara',
  tagline: null,
  color_primary: '#3b82f6',
  color_primary_dark: '#2563eb',
  logo_light_url: null,
  logo_dark_url: null,
}

const branding = ref<BrandingData>({ ...DEFAULT_BRANDING })
const loaded = ref(false)

/**
 * @brief Apply branding colors as CSS custom properties on :root.
 * @param data - Branding data to inject.
 */
function injectCssVariables(data: BrandingData): void {
  if (typeof document === 'undefined') return

  const root = document.documentElement
  root.style.setProperty('--color-primary', data.color_primary)
  root.style.setProperty('--color-primary-dark', data.color_primary_dark)
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
      const response = await fetch('/api/v1/branding/')
      if (!response.ok) return

      const data: BrandingData = await response.json()
      branding.value = data
      injectCssVariables(data)
      loaded.value = true
    } catch {
      branding.value = { ...DEFAULT_BRANDING }
      injectCssVariables(DEFAULT_BRANDING)
    }
  }

  return {
    branding: readonly(branding),
    loaded: readonly(loaded),
    fetchBranding,
  }
}
