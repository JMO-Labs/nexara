/**
 * @file lib/contrast.ts
 * @brief WCAG 2.1 contrast ratio helper for #RRGGBB colors.
 */

/** Relative luminance of a #RRGGBB color. */
function luminance(hex: string): number {
  const n = parseInt(hex.replace("#", ""), 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/**
 * @brief WCAG contrast ratio between two colors.
 * @param fg foreground hex (#RRGGBB)
 * @param bg background hex (#RRGGBB)
 * @return ratio from 1 to 21
 */
export function contrastRatio(fg: string, bg: string): number {
  const [a, b] = [luminance(fg), luminance(bg)];
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}
