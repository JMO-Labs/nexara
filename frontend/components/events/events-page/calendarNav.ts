/**
 * @file components/events/events-page/calendarNav.ts
 * @brief Friendly toolbar title for each calendar view.
 */
import { addDays, format } from "date-fns";
import type { CalendarView } from "@/components/events/CalendarViewSwitcher";

/**
 * @brief Title shown in the calendar toolbar for the active view.
 * @param view active calendar view
 * @param month first day of the visible month
 * @param weekStart Sunday starting the visible week
 * @param selectedDay selected day (day view), or null
 * @return display string, e.g. "November 2026", "Nov 15 – Nov 21"
 */
export function periodTitle(
  view: CalendarView,
  month: Date,
  weekStart: Date,
  selectedDay: Date | null,
): string {
  if (view === "week") {
    return `${format(weekStart, "MMM d")} – ${format(addDays(weekStart, 6), "MMM d")}`;
  }
  if (view === "day" && selectedDay) {
    return format(selectedDay, "EEEE, MMM d");
  }
  return format(month, "MMMM yyyy");
}
