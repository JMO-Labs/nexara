/**
 * @file components/trips/tripTime.ts
 * @brief Helpers for the datetime-local picker (viewer local time <-> UTC ISO).
 */

const p = (n: number) => String(n).padStart(2, "0");

/**
 * @param d date
 * @return value for <input type="datetime-local"> in local time
 */
export function toLocalInput(d: Date): string {
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

/**
 * @param offsetMin minutes from now
 * @return local input value
 */
export const localIn = (offsetMin: number) =>
  toLocalInput(new Date(Date.now() + offsetMin * 60_000));

/** @brief Allowed window for the picker: 10 minutes to 72 hours from now. */
export const tripWindow = () => ({ min: localIn(10), max: localIn(72 * 60) });

/**
 * @param value local input value
 * @return null when empty/outside the window, else the UTC ISO string
 */
export function toIso(value: string): string | null {
  const t = new Date(value).getTime();
  if (!value || Number.isNaN(t)) return null;
  const now = Date.now();
  if (t < now + 9.5 * 60_000 || t > now + 72 * 3_600_000) return null;
  return new Date(t).toISOString();
}

/**
 * @param iso UTC ISO string
 * @return short time in the viewer's locale and zone
 */
export const fmtTime = (iso: string) =>
  new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    hour: "numeric",
    minute: "2-digit",
  });
