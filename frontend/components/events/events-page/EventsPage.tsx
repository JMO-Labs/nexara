"use client";
/**
 * @file components/events/events-page/EventsPage.tsx
 * @brief Calendar page: PageHeader, toolbar, glass calendar panel, aside
 *        panels, detail drawer and create/edit modals.
 */
import * as React from "react";
import { addDays, addMonths, startOfWeek } from "date-fns";
import { cn } from "@/lib/utils";
import { EventCreateModal } from "@/components/events/EventCreateModal";
import { EventDetailPanel } from "@/components/events/EventDetailPanel";
import { CalendarFilterBar } from "@/components/events/CalendarFilterBar";
import { Button } from "@/components/ui";
import { Panel } from "@/components/ui/page/Panel";
import { PageHeader } from "@/components/ui/page/PageHeader";
import type { EventItem } from "@/lib/api/events";
import { useEventsPageState } from "./useEventsPageState";
import { EventsViewPane } from "./EventsViewPane";
import { EventsSidePanel } from "./EventsSidePanel";
import { periodTitle } from "./calendarNav";

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
  const unit = s.view === "week" ? "week" : s.view === "day" ? "day" : "month";

  /** Prev/next step by the active view's period. */
  const step = (dir: -1 | 1) => {
    if (s.view === "week") s.setWeekStart(addDays(s.weekStart, 7 * dir));
    else if (s.view === "day")
      s.setSelectedDay(addDays(s.selectedDay ?? new Date(), dir));
    else s.setMonth(addMonths(s.month, dir));
  };
  /** Jump to today within the active view's period. */
  const goToday = () => {
    const now = new Date();
    if (s.view === "week")
      s.setWeekStart(startOfWeek(now, { weekStartsOn: 0 }));
    else if (s.view === "day") s.setSelectedDay(now);
    else s.setMonth(now);
  };

  return (
    <div
      ref={wrapperRef}
      className="relative"
      style={{ paddingBottom: drawerReserve }}
    >
      <PageHeader
        title="Calendar"
        description="Everything coming up across your groups"
        actions={<Button onClick={() => setCreateOpen(true)}>New event</Button>}
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
        view={s.view}
        onViewChange={s.setView}
        title={periodTitle(s.view, s.month, s.weekStart, s.selectedDay)}
        unit={unit}
        onStep={step}
        onToday={goToday}
      />

      <div
        className={cn(
          "grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px] lg:gap-[18px]",
          s.view === "list" ? "lg:items-start" : "items-stretch",
        )}
      >
        <Panel as="div" className={cn("min-w-0 p-3 md:p-5")}>
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
        </Panel>
        <EventsSidePanel
          upcoming={s.upcoming}
          railEvents={s.railEvents}
          selectedDay={s.selectedDay}
          selectedEventId={s.selectedEventId}
          subgroupNames={s.subgroupNames}
          onSelectEvent={s.onSelectEvent}
          onClearDay={() => s.setSelectedDay(null)}
          onCreate={() => setCreateOpen(true)}
          showDayPanel={s.view !== "list"}
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
