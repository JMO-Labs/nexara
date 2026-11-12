"use client";
/**
 * @file components/admin/ThemeGallery.tsx
 * @brief Gallery of preset color themes; one click applies all colors.
 */
import { useApplyPreset, usePresetThemes } from "@/hooks/useBranding";
import type { PresetTheme } from "@/lib/api/branding";

const MAP = {
  color_primary: "primary",
  color_primary_dark: "primary_dark",
  color_accent: "accent",
  color_surface_light: "surface_light",
  color_surface_dark: "surface_dark",
  color_text_light: "text_light",
  color_text_dark: "text_dark",
} as const;

const SWATCHES = [
  "primary",
  "primary_dark",
  "accent",
  "surface_light",
  "surface_dark",
] as const;

function matches(t: PresetTheme, cur?: Record<string, string | undefined>) {
  if (!cur) return false;
  return Object.entries(MAP).every(
    ([k, v]) => cur[k]?.toLowerCase() === t[v].toLowerCase(),
  );
}

/**
 * @brief Preset theme cards.
 * @param current current branding colors (to mark the active theme)
 * @return gallery, or null while loading / on error
 */
export function ThemeGallery({
  current,
}: {
  current?: Record<string, string | undefined>;
}) {
  const { data } = usePresetThemes();
  const apply = useApplyPreset();
  if (!data?.themes.length) return null;
  return (
    <section aria-labelledby="preset-themes" className="flex flex-col gap-3">
      <h3 id="preset-themes" className="text-base font-semibold">
        Preset themes
      </h3>
      <p className="text-sm opacity-80">
        Preset themes — apply all colors in one click
      </p>
      <ul className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {data.themes.map((t) => {
          const active = matches(t, current);
          return (
            <li key={t.name}>
              <button
                type="button"
                aria-label={`Apply ${t.name}`}
                aria-pressed={active}
                disabled={apply.isPending}
                onClick={() => apply.mutate(t.name)}
                className={`flex w-full flex-col gap-2 rounded-lg border p-3 text-left focus-visible:outline focus-visible:outline-2 disabled:opacity-60 ${active ? "border-2 border-current" : ""}`}
              >
                <span className="flex gap-1" aria-hidden="true">
                  {SWATCHES.map((s) => (
                    <span
                      key={s}
                      className="h-6 w-6 rounded-full border"
                      style={{ backgroundColor: t[s] }}
                    />
                  ))}
                </span>
                <span className="font-medium">{t.name}</span>
                <span className="text-xs opacity-80">{t.description}</span>
                {active && <span className="text-xs font-medium">Current</span>}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
