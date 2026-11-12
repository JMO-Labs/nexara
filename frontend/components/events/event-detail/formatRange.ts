/**
 * @file components/events/event-detail/formatRange.ts
 * @brief Human date/time range for an event.
 */
import { format, parseISO } from "date-fns";

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
  const sDate = format(s, "EEE, MMM d, yyyy");
  if (allDay) {
    const eDate = format(e, "EEE, MMM d, yyyy");
    return sDate === eDate ? `${sDate} · All day` : `${sDate} → ${eDate}`;
  }
  const sameDay = format(s, "yyyy-MM-dd") === format(e, "yyyy-MM-dd");
  if (sameDay)
    return `${sDate} · ${format(s, "h:mm a")} – ${format(e, "h:mm a")}`;
  return `${sDate} ${format(s, "h:mm a")} → ${format(e, "EEE, MMM d")} ${format(e, "h:mm a")}`;
}
