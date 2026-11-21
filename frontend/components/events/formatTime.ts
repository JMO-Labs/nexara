/**
 * @file components/events/formatTime.ts
 * @brief Friendly lowercase clock time for calendar labels ("9 am", "9:30 am").
 */
import { format } from "date-fns";

/**
 * @brief Format a time of day; minutes are dropped when zero.
 * @param d date whose time is shown
 * @return e.g. "9 am", "9:30 am", "12 am"
 */
export function formatTime(d: Date): string {
  return format(d, d.getMinutes() === 0 ? "h aaa" : "h:mm aaa");
}
