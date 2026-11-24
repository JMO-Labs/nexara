/**
 * @file lib/notifications/pushTag.ts
 * @brief Notification tag, mirrors backend channels/push.py: type:thread when
 *        the payload has post_id/channel_id/event_id/target_id, else type.
 */
const THREAD_KEYS = ["post_id", "channel_id", "event_id", "target_id"] as const;

/** @param type notification type key @param p payload @return collapse tag */
export function pushTag(type: string, p: Record<string, unknown> = {}): string {
  const k = THREAD_KEYS.find((k) => p[k]);
  return k ? `${type}:${String(p[k])}` : type;
}

/** @brief Same-origin relative path guard (rejects //, /\\, schemes). */
export function safePath(u: unknown): string | null {
  return typeof u === "string" && /^\/(?![/\\])/.test(u) ? u : null;
}
