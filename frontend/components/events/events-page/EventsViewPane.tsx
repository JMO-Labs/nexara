"use client";
/**
 * @file components/events/events-page/EventsViewPane.tsx
 * @brief Renders the active calendar view (month / week / day / list) plus
 *        loading (staggered skeleton), error (Retry) and empty (CTA) states.
 */
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { MonthCalendarLarge } from "@/components/events/MonthCalendarLarge";
import { WeekView } from "@/components/events/WeekView";
import { DayView } from "@/components/events/DayView";
import { ListView } from "@/components/events/ListView";
import type { CalendarView } from "@/components/events/CalendarViewSwitcher";
import type { EventItem } from "@/lib/api/events";

export interface EventsViewPaneProps {
  view: CalendarView;
  events: EventItem[];
  /** Fetch state of `events`. */
  status: "loading" | "error" | "ready";
  onRetry: () => void;
  onCreate: () => void;
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

function LoadingState() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Loading events"
      className="flex flex-col gap-3"
    >
      {[0, 1, 2, 3].map((i) => (
        <Skeleton
          key={i}
          role="presentation"
          aria-busy={undefined}
          aria-live={undefined}
          height={96}
          rounded="lg"
          style={{ animationDelay: `${i * 80}ms` }}
        />
      ))}
    </div>
  );
}

/**
 * @brief Active view with loading / error / empty handling.
 * @param props see EventsViewPaneProps
 * @return view or state element
 */
export function EventsViewPane(p: EventsViewPaneProps) {
  if (p.status === "loading") return <LoadingState />;
  if (p.status === "error") {
    return (
      <EmptyState
        title="Couldn't load events"
        description="Something went wrong. Please try again."
        action={
          <Button variant="ghost" onClick={p.onRetry}>
            Retry
          </Button>
        }
      />
    );
  }
  if (p.events.length > 0) return <ActiveView {...p} />;
  const empty = (
    <EmptyState
      compact
      title="No events. Create one!"
      description="Once events are scheduled they'll appear here."
      action={<Button onClick={p.onCreate}>Create event</Button>}
    />
  );
  if (p.view === "list") return empty;
  return (
    <div className="flex flex-col gap-2">
      {empty}
      <ActiveView {...p} />
    </div>
  );
}

/**
 * @brief Active calendar view. Period navigation lives in the page toolbar.
 * @param props see EventsViewPaneProps
 * @return view element
 */
function ActiveView(p: EventsViewPaneProps) {
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
      <div className="h-full">
        <WeekView {...common} weekStart={p.weekStart} />
      </div>
    );
  }
  if (p.view === "day") {
    if (!p.selectedDay) {
      return (
        <EmptyState
          compact
          title="Select a day"
          description="Pick a day in the month view."
        />
      );
    }
    return (
      <div className="h-full">
        <DayView {...common} day={p.selectedDay} />
      </div>
    );
  }
  return (
    <div className="h-full">
      <ListView {...common} />
    </div>
  );
}
