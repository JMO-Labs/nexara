/**
 * @file components/prompts/stackPlacement.ts
 * @brief Pure helpers placing the questions stack on the feed timeline.
 */

/**
 * @brief Index at which to insert the stack: before the first item older
 *        than `firedAt`; end of list if none; 0 if empty.
 * @param items feed items (newest first) with created_at
 * @param firedAt ISO fired time of the newest daily question
 * @return insertion index
 */
export function stackIndex(
  items: { created_at: string }[],
  firedAt: string,
): number {
  const t = Date.parse(firedAt);
  const i = items.findIndex((x) => Date.parse(x.created_at) < t);
  return i === -1 ? items.length : i;
}

/**
 * @brief "Today" / "Yesterday" / short date for an ISO time.
 * @param iso ISO time
 * @param now reference time
 * @return label
 */
export function dayLabel(iso: string, now: Date = new Date()): string {
  // Date-only strings ("2026-11-23") are local calendar days, not UTC.
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  const d = m ? new Date(+m[1], +m[2] - 1, +m[3]) : new Date(iso);
  const start = (x: Date) =>
    new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diff = Math.round((start(now) - start(d)) / 86_400_000);
  if (diff <= 0) return "Today";
  if (diff === 1) return "Yesterday";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
