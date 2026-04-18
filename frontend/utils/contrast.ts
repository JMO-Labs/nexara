/**
 * @file utils/contrast.ts
 * @brief WCAG contrast ratio utilities for ColorPicker.
 */

const HEX_COLOR_RE = /^#[0-9a-fA-F]{6}$/;

/**
 * @brief Convert #RRGGBB to sRGB values (0-1).
 */
function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace(/^#/, "");
  return [
    parseInt(clean.slice(0, 2), 16) / 255,
    parseInt(clean.slice(2, 4), 16) / 255,
    parseInt(clean.slice(4, 6), 16) / 255,
  ];
}

/**
 * @brief Convert sRGB component to linear luminance.
 */
function linearize(c: number): number {
  if (c <= 0.03928) return c / 12.92;
  return ((c + 0.055) / 1.055) ** 2.4;
}

/**
 * @brief Compute relative luminance (WCAG 2.1).
 * @param hex 6-digit hex string (#RRGGBB).
 * @returns Luminance in [0, 1].
 */
export function relativeLuminance(hex: string): number {
  if (!HEX_COLOR_RE.test(hex)) return 0;
  const [r, g, b] = hexToRgb(hex);
  return (
    0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)
  );
}

/**
 * @brief Compute contrast ratio (WCAG 2.1).
 * @param color1 First hex color.
 * @param color2 Second hex color.
 * @returns Contrast ratio (1.0 to 21.0).
 */
export function contrastRatio(color1: string, color2: string): number {
  const l1 = relativeLuminance(color1);
  const l2 = relativeLuminance(color2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}
