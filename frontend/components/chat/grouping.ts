/**
 * @file components/chat/grouping.ts
 * @brief Pure helpers for chat message grouping and day separators.
 *        Note: grouping requires same day AND <5 min, so a 23:58 -> 00:01
 *        run from one sender is split by a day separator (intended).
 */
import { format, isSameDay, subDays } from "date-fns";
import type { ChatMessage } from "@/lib/api/chat";

const GROUP_GAP_MS = 5 * 60 * 1000;

/**
 * @brief Whether `cur` continues `prev` (same sender, <5 min, same day).
 * @param prev previous message in render order
 * @param cur current message
 * @return true when the header should be shared
 */
export function isGrouped(
  prev: ChatMessage | undefined,
  cur: ChatMessage,
): boolean {
  if (!prev) return false;
  if (prev.author?.id !== cur.author?.id) return false;
  const a = new Date(prev.created_at);
  const b = new Date(cur.created_at);
  return isSameDay(a, b) && Math.abs(b.getTime() - a.getTime()) < GROUP_GAP_MS;
}

/**
 * @brief Day separator label.
 * @param iso ISO timestamp
 * @param now reference time (injectable for tests)
 * @return "Today", "Yesterday" or "Month D, YYYY"
 */
export function dayLabel(iso: string, now: Date = new Date()): string {
  const d = new Date(iso);
  if (isSameDay(d, now)) return "Today";
  if (isSameDay(d, subDays(now, 1))) return "Yesterday";
  return format(d, "MMMM d, yyyy");
}

/**
 * @brief Whether a date separator precedes `cur`.
 * @param prev previous message
 * @param cur current message
 * @return true on first message or day change
 */
export function startsNewDay(
  prev: ChatMessage | undefined,
  cur: ChatMessage,
): boolean {
  return (
    !prev || !isSameDay(new Date(prev.created_at), new Date(cur.created_at))
  );
}
