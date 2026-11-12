/**
 * @file components/notifications/formatTime.ts
 * @brief Relative time formatting shared by notification rows.
 */

/**
 * @brief Relative time string.
 * @param iso ISO timestamp
 * @return "just now", "Nm ago", "Nh ago" or a locale date
 */
export function formatTime(iso: string): string {
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86_400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString();
}
