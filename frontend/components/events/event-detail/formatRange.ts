/**
 * @file components/events/event-detail/formatRange.ts
 * @brief Human date/time range for an event: "Sat, Nov 21 · 9 am to 11 am".
 *        The year is shown only when it is not the current year.
 */
import { format, isSameYear, parseISO } from "date-fns";
import { formatTime } from "../formatTime";

/**
 * @brief Format a day, adding the year only outside the current year.
 * @param d date to format
 * @return e.g. "Sat, Nov 21" or "Sat, Nov 21, 2031"
 */
function dayLabel(d: Date): string {
  return format(
    d,
    isSameYear(d, new Date()) ? "EEE, MMM d" : "EEE, MMM d, yyyy",
  );
}

/**
 * @brief Format an event's start/end as a single line.
 * @param starts ISO start
 * @param ends ISO end
 * @param allDay whether the event is all-day
 * @return display string
 */
export function formatRange(
  starts: string,
  ends: string,
  allDay: boolean,
): string {
  const s = parseISO(starts);
  const e = parseISO(ends);
  const sDate = dayLabel(s);
  if (allDay) {
    const eDate = dayLabel(e);
    return sDate === eDate ? `${sDate} · All day` : `${sDate} → ${eDate}`;
  }
  const sameDay = format(s, "yyyy-MM-dd") === format(e, "yyyy-MM-dd");
  if (sameDay) return `${sDate} · ${formatTime(s)} to ${formatTime(e)}`;
  return `${sDate} ${formatTime(s)} → ${dayLabel(e)} ${formatTime(e)}`;
}
