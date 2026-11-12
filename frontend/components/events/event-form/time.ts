/**
 * @file components/events/event-form/time.ts
 * @brief Local date/time helpers for the event form.
 */
const PAD = (n: number) => String(n).padStart(2, "0");

/**
 * @brief Split an ISO string into local date (YYYY-MM-DD) and time (HH:mm).
 * @param iso ISO timestamp
 * @return local date and time strings
 */
export function splitLocal(iso: string): { date: string; time: string } {
  const d = new Date(iso);
  return {
    date: `${d.getFullYear()}-${PAD(d.getMonth() + 1)}-${PAD(d.getDate())}`,
    time: `${PAD(d.getHours())}:${PAD(d.getMinutes())}`,
  };
}

/**
 * @brief Today's local date as YYYY-MM-DD.
 * @return date string
 */
export function todayDate(): string {
  return splitLocal(new Date().toISOString()).date;
}

/**
 * @brief Compose local date + HH:mm into an ISO string.
 * @param date YYYY-MM-DD
 * @param time HH:mm
 * @return ISO timestamp
 */
export function composeIso(date: string, time: string): string {
  const [h, m] = time.split(":").map(Number);
  const [y, mo, d] = date.split("-").map(Number);
  return new Date(y, mo - 1, d, h, m, 0, 0).toISOString();
}

export const DEFAULT_START_TIME = "09:00";
export const DEFAULT_END_TIME = "10:00";
