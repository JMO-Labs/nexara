/**
 * @file lib/groupColor.ts
 * @brief Deterministic accent color for a group (subgroup).
 */

/** @brief Fallback palette for groups without an accent color. */
export const GROUP_PALETTE = [
  "#83A2DB",
  "#D0965E",
  "#45A29C",
  "#A485C8",
  "#CE6969",
  "#7FA35B",
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
  if (subgroupId === null) return "var(--nx-blue)";
  let sum = 0;
  for (let i = 0; i < subgroupId.length; i++) sum += subgroupId.charCodeAt(i);
  return GROUP_PALETTE[sum % GROUP_PALETTE.length];
}
