"use client";
/**
 * @file components/admin/ThemeGallery.tsx
 * @brief Gallery of preset colour themes; click a card to apply it.
 */
import { useApplyPreset, usePresetThemes } from "@/hooks/useBranding";
import type { Branding, PresetTheme } from "@/lib/api/branding";

const MAP = [
  ["primary", "color_primary"],
  ["primary_dark", "color_primary_dark"],
  ["accent", "color_accent"],
  ["surface_light", "color_surface_light"],
  ["surface_dark", "color_surface_dark"],
] as const;

function matches(t: PresetTheme, b: Branding): boolean {
  return (
    [
      "primary",
      "primary_dark",
      "accent",
      "surface_light",
      "surface_dark",
      "text_light",
      "text_dark",
    ] as const
  ).every(
    (k) =>
      b[`color_${k}` as keyof Branding]?.toString().toLowerCase() ===
      t[k].toLowerCase(),
  );
}

/**
 * @brief Preset theme cards.
 * @param current currently saved branding, used to mark the active preset
 */
export function ThemeGallery({ current }: { current: Branding }) {
  const { data } = usePresetThemes();
  const apply = useApplyPreset();
  if (!data?.themes?.length) return null;
  const pendingName = apply.isPending ? apply.variables : null;
  return (
    <section aria-labelledby="preset-themes-h" className="flex flex-col gap-3">
      <h3 id="preset-themes-h" className="text-base font-semibold">
        Preset themes
      </h3>
      <p className="text-sm text-muted-foreground">
        Preset themes — apply all colors in one click
      </p>
      <ul className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {data.themes.map((t) => {
          const active = matches(t, current);
          return (
            <li key={t.name}>
              <button
                type="button"
                aria-pressed={active}
                aria-label={`Apply ${t.name} theme`}
                disabled={apply.isPending}
                onClick={() => apply.mutate(t.name)}
                className={`w-full rounded-lg border p-3 text-left focus-visible:outline focus-visible:outline-2 disabled:opacity-60 ${active ? "border-2 border-current" : ""}`}
              >
                <span className="flex gap-1" aria-hidden="true">
                  {MAP.map(([k]) => (
                    <span
                      key={k}
                      className="h-6 w-6 rounded-full border"
                      style={{ backgroundColor: t[k] }}
                    />
                  ))}
                </span>
                <span className="mt-2 block text-sm font-medium">{t.name}</span>
                <span className="block text-xs">
                  {pendingName === t.name
                    ? "Applying…"
                    : active
                      ? "Selected"
                      : t.description}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
