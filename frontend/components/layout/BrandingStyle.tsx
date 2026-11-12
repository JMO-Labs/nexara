"use client";
/**
 * @file components/layout/BrandingStyle.tsx
 * @brief Applies community branding at runtime: sets palette and font CSS
 *        vars on <html> (light or dark values, following the `.dark` class)
 *        and publishes name/logo to the branding store. Renders nothing.
 */
import { useEffect } from "react";
import { useBranding } from "@/hooks/useBranding";
import { BRANDING_VARS, brandingVars } from "@/lib/brandingVars";
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
    const apply = () => {
      const vars = brandingVars(data, root.classList.contains("dark"));
      for (const name of BRANDING_VARS) {
        const v = vars[name];
        if (v) root.style.setProperty(name, v);
        else root.style.removeProperty(name);
      }
    };
    apply();
    setBrand(data.community_name, data.logo_light_url);
    const observer = new MutationObserver(apply);
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });
    return () => {
      observer.disconnect();
      for (const name of BRANDING_VARS) root.style.removeProperty(name);
    };
  }, [data, setBrand]);

  return null;
}
