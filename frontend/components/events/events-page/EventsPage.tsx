"use client";
/**
 * @file components/events/events-page/EventsPage.tsx
 * @brief Events page composition: masthead, filters, view switcher, active
 *        view, side rail, detail panel and create/edit modals.
 */
import * as React from "react";
import { EventCreateModal } from "@/components/events/EventCreateModal";
import { EventDetailPanel } from "@/components/events/EventDetailPanel";
import { CalendarViewSwitcher } from "@/components/events/CalendarViewSwitcher";
import { CalendarFilterBar } from "@/components/events/CalendarFilterBar";
import { PageMasthead } from "@/components/layout/PageMasthead";
import type { EventItem } from "@/lib/api/events";
import { useEventsPageState } from "./useEventsPageState";
import { EventsViewPane } from "./EventsViewPane";
import { EventsSidePanel } from "./EventsSidePanel";

const PERIOD: Record<string, string> = {
  month: "this month",
  week: "this week",
  day: "this day",
  list: "in view",
};

/**
 * @brief The /app/events screen.
 * @return page element
 */
export function EventsPage() {
  const s = useEventsPageState();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [editEvent, setEditEvent] = React.useState<EventItem | null>(null);
  const wrapperRef = React.useRef<HTMLDivElement | null>(null);
  const drawerReserve = s.selectedEvent ? 296 : 0;
  const n = s.filtered.length;

  return (
    <div
      ref={wrapperRef}
      className="relative flex min-h-full w-full flex-col px-3 py-4 md:px-4 md:py-5"
      style={{ paddingBottom: drawerReserve + 24 }}
    >
      <PageMasthead
        title="Events"
        meta={`${n} ${n === 1 ? "event" : "events"} ${PERIOD[s.view]}`}
        size="md"
      />

      <CalendarFilterBar
        month={s.month}
        onMonthChange={s.setMonth}
        selected={s.selectedSources}
        onSelectedChange={(ids) => {
          s.setSelectedSources(ids);
          s.setSelectedEventId(null);
        }}
        calendars={s.calendarList}
        onCreate={() => setCreateOpen(true)}
      />

      <CalendarViewSwitcher value={s.view} onChange={s.setView} />

      <div className="grid min-h-0 flex-1 items-start gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0">
          <EventsViewPane
            view={s.view}
            events={s.filtered}
            status={s.isLoading ? "loading" : s.isError ? "error" : "ready"}
            onRetry={() => void s.refetch()}
            onCreate={() => setCreateOpen(true)}
            month={s.month}
            weekStart={s.weekStart}
            onWeekStartChange={s.setWeekStart}
            selectedDay={s.selectedDay}
            onSelectedDayChange={s.setSelectedDay}
            selectedEventId={s.selectedEventId}
            subgroupNames={s.subgroupNames}
            onSelectDay={s.onSelectDay}
            onSelectEvent={s.onSelectEvent}
          />
        </div>
        <EventsSidePanel
          nextEvent={s.nextEvent}
          events={s.filtered}
          month={s.month}
          onMonthChange={s.setMonth}
          railEvents={s.railEvents}
          selectedDay={s.selectedDay}
          selectedEventId={s.selectedEventId}
          subgroupNames={s.subgroupNames}
          onSelectEvent={s.onSelectEvent}
          onClearDay={() => s.setSelectedDay(null)}
        />
      </div>

      <EventDetailPanel
        containerRef={wrapperRef}
        event={s.selectedEvent}
        subgroupNames={s.subgroupNames}
        onClose={() => s.setSelectedEventId(null)}
        onEdit={(ev) => setEditEvent(ev)}
      />

      <EventCreateModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
      />
      <EventCreateModal
        open={!!editEvent}
        event={editEvent}
        onClose={() => setEditEvent(null)}
      />
    </div>
  );
}

export default EventsPage;
