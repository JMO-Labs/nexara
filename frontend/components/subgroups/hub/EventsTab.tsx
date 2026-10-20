"use client";
/**
 * @file components/subgroups/hub/EventsTab.tsx
 * @brief Events tab: month calendar + day rail scoped to the subgroup.
 *        Mirrors the calendar page layout (MonthCalendarLarge + EventRail)
 *        but locked to this group's events. Members get a "New event" button.
 */
import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import {
  endOfMonth,
  isSameDay,
  parseISO,
  startOfDay,
  startOfMonth,
} from "date-fns";
import { Button } from "@/components/ui";
import { MonthCalendarLarge } from "@/components/events/MonthCalendarLarge";
import { EventRail } from "@/components/events/EventRail";
import { EventDetailPanel } from "@/components/events/EventDetailPanel";
import { EventCreateModal } from "@/components/events/EventCreateModal";
import { useEventsInRange } from "@/hooks/useEvents";
import type { SubgroupDetail } from "@/lib/api/subgroups";
import type { EventItem } from "@/lib/api/events";

export interface EventsTabProps {
  subgroup: SubgroupDetail;
}

export function EventsTab({ subgroup }: EventsTabProps) {
  const [createOpen, setCreateOpen] = React.useState(false);
  const [editEvent, setEditEvent] = React.useState<EventItem | null>(null);
  const [month, setMonth] = React.useState(() => startOfMonth(new Date()));
  const [selectedDay, setSelectedDay] = React.useState<Date | null>(() =>
    startOfDay(new Date()),
  );
  const [selectedEventId, setSelectedEventId] = React.useState<string | null>(
    null,
  );

  const monthStart = React.useMemo(() => startOfMonth(month), [month]);
  const monthEnd = React.useMemo(() => endOfMonth(month), [month]);

  const { data, isLoading } = useEventsInRange(
    monthStart,
    monthEnd,
    subgroup.id,
  );
  const events = React.useMemo(() => data?.items ?? [], [data?.items]);

  const subgroupNames = React.useMemo(
    () => new Map<string, string>([[subgroup.id, subgroup.name]]),
    [subgroup.id, subgroup.name],
  );

  const railEvents = React.useMemo(() => {
    if (!selectedDay) return events;
    return events.filter((ev) => {
      const s = startOfDay(parseISO(ev.starts_at));
      const e = startOfDay(parseISO(ev.ends_at));
      return selectedDay >= s && selectedDay <= e;
    });
  }, [events, selectedDay]);

  const selectedEvent = React.useMemo(
    () => events.find((e) => e.id === selectedEventId) ?? null,
    [events, selectedEventId],
  );

  const onSelectDay = (d: Date) => {
    setSelectedDay((prev) => (prev && isSameDay(prev, d) ? null : d));
  };

  const onSelectEvent = (ev: EventItem) => {
    setSelectedEventId(ev.id);
    setSelectedDay(startOfDay(parseISO(ev.starts_at)));
  };

  const wrapperRef = React.useRef<HTMLDivElement | null>(null);
  const canCreate = !!subgroup.my_role;

  return (
    <div ref={wrapperRef} className="relative min-h-96">
      <div className="mb-4 flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-muted">
          {events.length} {events.length === 1 ? "event" : "events"} this month
        </p>
        {canCreate && (
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            New event
          </Button>
        )}
      </div>

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div
          className={`min-w-0 transition-opacity ${isLoading ? "opacity-60" : ""}`}
        >
          <MonthCalendarLarge
            events={events}
            month={month}
            selectedDay={selectedDay}
            selectedEventId={selectedEventId}
            subgroupNames={subgroupNames}
            onSelectDay={onSelectDay}
            onSelectEvent={onSelectEvent}
          />
          <div className="mt-2 flex justify-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              className="min-h-11"
              onClick={() =>
                setMonth((m) =>
                  startOfMonth(new Date(m.getFullYear(), m.getMonth() - 1, 1)),
                )
              }
            >
              <ChevronLeft className="size-4" aria-hidden /> Prev
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="min-h-11"
              onClick={() => setMonth(startOfMonth(new Date()))}
            >
              Today
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="min-h-11"
              onClick={() =>
                setMonth((m) =>
                  startOfMonth(new Date(m.getFullYear(), m.getMonth() + 1, 1)),
                )
              }
            >
              Next <ChevronRight className="size-4" aria-hidden />
            </Button>
          </div>
        </div>

        <div className="flex h-auto flex-col overflow-hidden rounded-2xl bg-surface lg:sticky lg:top-4 lg:h-[calc(100vh-200px)]">
          <div className="flex items-center justify-between border-b border-current/15 px-4 py-2.5 text-sm font-semibold text-muted">
            <span>{selectedDay ? "This day" : "This month"}</span>
            {selectedDay && (
              <button
                type="button"
                onClick={() => setSelectedDay(null)}
                className="min-h-11 px-2 text-xs outline-none hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Clear
              </button>
            )}
          </div>
          <div className="min-h-0 flex-1">
            <EventRail
              events={railEvents}
              selectedDay={selectedDay}
              selectedEventId={selectedEventId}
              subgroupNames={subgroupNames}
              onSelectEvent={onSelectEvent}
            />
          </div>
        </div>
      </div>

      <EventDetailPanel
        containerRef={wrapperRef}
        event={selectedEvent}
        subgroupNames={subgroupNames}
        onClose={() => setSelectedEventId(null)}
        onEdit={(ev) => setEditEvent(ev)}
      />

      <EventCreateModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        defaultSubgroupId={subgroup.id}
      />
      <EventCreateModal
        open={!!editEvent}
        event={editEvent}
        onClose={() => setEditEvent(null)}
      />
    </div>
  );
}

export default EventsTab;
