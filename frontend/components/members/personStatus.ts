/**
 * @file components/members/personStatus.ts
 * @brief Human status line for a directory person.
 */

/**
 * @brief Compact relative time such as "3h ago".
 * @param iso ISO timestamp
 * @return relative string
 */
export function relative(iso: string): string {
  const mins = Math.max(0, Math.floor((Date.now() - Date.parse(iso)) / 60_000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

/**
 * @brief Status text for a person.
 * @param p online flag and last-seen time
 * @return status, or "" when nothing is known
 */
export function statusOf(p: {
  online: boolean;
  last_seen_at: string | null;
}): string {
  if (p.online) return "Online now";
  if (p.last_seen_at) return `Active ${relative(p.last_seen_at)}`;
  return "";
}
