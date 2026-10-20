/**
 * @file lib/groupVisuals.ts
 * @brief Deterministic visual identity utilities for groups.
 *        Hash, gradient, and monogram generation.
 */

/**
 * Deterministic 32-bit hash for stable hue/angle per slug.
 * @param s The slug to hash
 * @return A 32-bit unsigned integer
 */
export function hashSlug(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/**
 * Generate a deterministic gradient and monogram background for a group slug.
 * @param slug The group slug
 * @return Object with background (linear-gradient string) and monogramBg (hsl string)
 */
export function gradientFor(slug: string): {
  background: string;
  monogramBg: string;
} {
  const h = hashSlug(slug || "group");
  const hue1 = h % 360;
  const hue2 = (hue1 + 38 + ((h >>> 8) % 60)) % 360;
  const angle = (h >>> 16) % 360;
  return {
    background: `linear-gradient(${angle}deg,
      hsl(${hue1} 62% 32%) 0%,
      hsl(${hue2} 58% 22%) 70%,
      hsl(${(hue1 + 200) % 360} 40% 14%) 100%)`,
    monogramBg: `hsl(${hue1} 38% 92%)`,
  };
}

/**
 * Generate a two-character monogram from a group name.
 * Single word: first two chars. Multi-word: first letter of first and last word.
 * @param name The group name
 * @return Two-character uppercase monogram, or middle dot if name is empty
 */
export function monogram(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "·";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
