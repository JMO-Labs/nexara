/**
 * @file lib/groupColor.ts
 * @brief Deterministic accent color for a group (subgroup).
 */

/**
 * @brief Fallback "door" palette for groups without an accent color: the
 *        painted doors of the Aegean theme (Aegean blue, bougainvillea,
 *        olive, ochre, harbor, fig).
 */
export const GROUP_PALETTE = [
  "#2F5873",
  "#A8505F",
  "#7A8A55",
  "#C9973F",
  "#5C8FA8",
  "#7D5A7A",
] as const;

/**
 * @brief Resolve a group's display color.
 * @param subgroupId Group id, or null for community-wide.
 * @param accent Explicit accent color, if set.
 * @return Accent, blue token for null id, else stable palette color.
 */
export function groupColor(
  subgroupId: string | null,
  accent?: string | null,
): string {
  if (accent) return accent;
  if (subgroupId === null) return "var(--nx-blue)"; // community-wide: sea glass
  let sum = 0;
  for (let i = 0; i < subgroupId.length; i++) sum += subgroupId.charCodeAt(i);
  return GROUP_PALETTE[sum % GROUP_PALETTE.length];
}
