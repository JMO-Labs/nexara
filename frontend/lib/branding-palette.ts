/**
 * @file lib/branding-palette.ts
 * @brief Palette field metadata, font lists and contrast-pair checks.
 */
import { contrastRatio } from "@/lib/contrast";

export const HEX_RE = /^#[0-9a-fA-F]{6}$/;

export type ColorKey =
  | "color_primary"
  | "color_primary_dark"
  | "color_accent"
  | "color_surface_light"
  | "color_surface_dark"
  | "color_text_light"
  | "color_text_dark";

export const COLOR_FIELDS: { key: ColorKey; label: string; def: string }[] = [
  { key: "color_primary", label: "Primary", def: "#2f6b45" },
  { key: "color_primary_dark", label: "Primary (dark)", def: "#7bc28f" },
  { key: "color_accent", label: "Accent color", def: "#C6B4F5" },
  { key: "color_surface_light", label: "Surface (light)", def: "#ffffff" },
  { key: "color_surface_dark", label: "Surface (dark)", def: "#1f2937" },
  { key: "color_text_light", label: "Text (light)", def: "#111827" },
  { key: "color_text_dark", label: "Text (dark)", def: "#f9fafb" },
];

export const SANS_FONTS = [
  "Inter",
  "Roboto",
  "Open Sans",
  "Lato",
  "Poppins",
  "Nunito",
  "system-ui",
  "Arial",
  "Georgia",
];
export const MONO_FONTS = [
  "JetBrains Mono",
  "Fira Code",
  "Source Code Pro",
  "IBM Plex Mono",
  "ui-monospace",
  "Courier New",
];

export interface PairCheck {
  id: string;
  label: string;
  ratio: number;
  min: number;
  ok: boolean;
}

/**
 * @brief Contrast checks for text/surface (4.5) and primary/surface (3, large).
 * @param c palette values keyed by ColorKey
 * @return one check per pair; invalid hex pairs are skipped
 */
export function checkPairs(c: Record<ColorKey, string>): PairCheck[] {
  const defs: [string, string, ColorKey, ColorKey, number][] = [
    [
      "tl",
      "Text on light surface",
      "color_text_light",
      "color_surface_light",
      4.5,
    ],
    [
      "td",
      "Text on dark surface",
      "color_text_dark",
      "color_surface_dark",
      4.5,
    ],
    [
      "pl",
      "Primary on light surface (large text)",
      "color_primary",
      "color_surface_light",
      3,
    ],
    [
      "pd",
      "Primary on dark surface (large text)",
      "color_primary_dark",
      "color_surface_dark",
      3,
    ],
  ];
  return defs
    .filter(([, , a, b]) => HEX_RE.test(c[a]) && HEX_RE.test(c[b]))
    .map(([id, label, a, b, min]) => {
      const ratio = contrastRatio(c[a], c[b]);
      return { id, label, ratio, min, ok: ratio >= min };
    });
}
