/**
 * @file components/chat/format.ts
 * @brief Small time/presence formatters for chat lists, header and details.
 */

/**
 * @brief Compact relative time: "now", "5m", "2h", "3d", else a short date.
 * @param iso ISO timestamp
 * @param now reference time (default: current)
 */
export function agoShort(iso: string, now: Date = new Date()): string {
  const s = Math.max(0, (now.getTime() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "now";
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  if (s < 7 * 86400) return `${Math.floor(s / 86400)}d`;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  }).format(new Date(iso));
}

/**
 * @brief "Online" / "Active 2h ago" / null when unknown.
 * @param online peer is online
 * @param lastSeen ISO or null (null when hidden)
 */
export function presenceText(
  online: boolean,
  lastSeen: string | null,
  now: Date = new Date(),
): string | null {
  if (online) return "Online";
  if (!lastSeen) return null;
  const a = agoShort(lastSeen, now);
  return a === "now" ? "Active just now" : `Active ${a} ago`;
}

/**
 * @brief Clock time in an IANA zone ("4:12 PM"); null for a bad zone.
 */
export function localTime(tz: string, now: Date = new Date()): string | null {
  try {
    return new Intl.DateTimeFormat(undefined, {
      hour: "numeric",
      minute: "2-digit",
      timeZone: tz,
    }).format(now);
  } catch {
    return null;
  }
}

/** @brief "today", "tomorrow" or "in N days". */
export function inDays(n: number): string {
  if (n <= 0) return "today";
  if (n === 1) return "tomorrow";
  return `in ${n} days`;
}
