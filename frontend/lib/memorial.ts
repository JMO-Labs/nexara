/**
 * @file lib/memorial.ts
 * @brief Memorial date helpers.
 */

const year = (d?: string | null) =>
  d && /^\d{4}/.test(d) ? d.slice(0, 4) : "";

/**
 * @brief Life span text such as "1931 – 2026".
 * @param born ISO birthday, or "--MM-DD" when the year is hidden
 * @param passed ISO passed-on date
 * @return "1931 – 2026", "Passed 2026", "1931" or ""
 */
export function lifespan(born?: string | null, passed?: string | null): string {
  const b = year(born);
  const p = year(passed);
  if (b && p) return `${b} – ${p}`;
  if (p) return `Passed ${p}`;
  return b;
}
