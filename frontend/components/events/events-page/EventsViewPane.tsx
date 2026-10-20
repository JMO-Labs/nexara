"use client";
/**
 * @file components/events/events-page/EventsViewPane.tsx
 * @brief Renders the active calendar view (month / week / day / list).
 */
import { addDays } from "date-fns";
import { MonthCalendarLarge } from "@/components/events/MonthCalendarLarge";
import { WeekView } from "@/components/events/WeekView";
import { DayView } from "@/components/events/DayView";
import { ListView } from "@/components/events/ListView";
import type { CalendarView } from "@/components/events/CalendarViewSwitcher";
import type { EventItem } from "@/lib/api/events";
import { PeriodNav } from "./PeriodNav";

export interface EventsViewPaneProps {
  view: CalendarView;
  events: EventItem[];
  month: Date;
  weekStart: Date;
  onWeekStartChange: (d: Date) => void;
  selectedDay: Date | null;
  onSelectedDayChange: (fn: (prev: Date | null) => Date | null) => void;
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectDay: (d: Date) => void;
  onSelectEvent: (ev: EventItem) => void;
}

/**
 * @brief Active view with its period navigation.
 * @param props see EventsViewPaneProps
 * @return view element
 */
export function EventsViewPane(p: EventsViewPaneProps) {
  const common = {
    events: p.events,
    subgroupNames: p.subgroupNames,
    selectedEventId: p.selectedEventId,
    onSelectEvent: p.onSelectEvent,
  };
  if (p.view === "month") {
    return (
      <MonthCalendarLarge
        {...common}
        month={p.month}
        selectedDay={p.selectedDay}
        onSelectDay={p.onSelectDay}
      />
    );
  }
  if (p.view === "week") {
    return (
      <div className="flex h-full flex-col gap-2">
        <PeriodNav
          unit="week"
          label={`Week of ${p.weekStart.toLocaleDateString()}`}
          onPrev={() => p.onWeekStartChange(addDays(p.weekStart, -7))}
          onNext={() => p.onWeekStartChange(addDays(p.weekStart, 7))}
        />
        <div className="min-h-0 flex-1">
          <WeekView {...common} weekStart={p.weekStart} />
        </div>
      </div>
    );
  }
  if (p.view === "day") {
    return (
      <div className="flex h-full flex-col gap-2">
        <PeriodNav
          unit="day"
          label={
            p.selectedDay ? p.selectedDay.toLocaleDateString() : "Select a day"
          }
          onPrev={() =>
            p.onSelectedDayChange((prev) => (prev ? addDays(prev, -1) : null))
          }
          onNext={() =>
            p.onSelectedDayChange((prev) => (prev ? addDays(prev, 1) : null))
          }
        />
        {p.selectedDay && (
          <div className="min-h-0 flex-1">
            <DayView {...common} day={p.selectedDay} />
          </div>
        )}
      </div>
    );
  }
  return (
    <div className="h-full">
      <ListView {...common} />
    </div>
  );
}
