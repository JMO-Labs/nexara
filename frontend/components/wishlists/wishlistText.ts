/**
 * @file components/wishlists/wishlistText.ts
 * @brief Display helpers for wishlists: dates, countdowns, recipients.
 */
import type { Recipient } from "@/lib/api/wishlists";

/** @brief "December 12" (no year) from an ISO date. */
export const dayLabel = (d: string | null) =>
  d
    ? new Date(`${d}T00:00:00`).toLocaleDateString(undefined, {
        month: "long",
        day: "numeric",
      })
    : null;

/** @brief Whole days from today until an ISO date (negative when past). */
export function daysUntil(d: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round(
    (new Date(`${d}T00:00:00`).getTime() - today.getTime()) / 86_400_000,
  );
}

/** @brief "Today", "Tomorrow", "In 12 days", "3 days ago". */
export function countdown(d: string): string {
  const n = daysUntil(d);
  if (n === 0) return "Today";
  if (n === 1) return "Tomorrow";
  if (n > 1) return `In ${n} days`;
  return n === -1 ? "Yesterday" : `${-n} days ago`;
}

/** @brief "Biscuit", "Leo and Maya", "Leo, Maya and 2 more", "Everyone". */
export function recipientsText(rs: Recipient[]): string {
  const names = rs.map((r) => r.name);
  if (names.length <= 2) return names.join(" and ");
  return `${names.slice(0, 2).join(", ")} and ${names.length - 2} more`;
}
