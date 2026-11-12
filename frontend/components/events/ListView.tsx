"use client";
/**
 * @file components/events/ListView.tsx
 * @brief List view grouped by date. Event rows with color bar.
 */
import * as React from "react";
import { format, parseISO, startOfDay, isSameDay } from "date-fns";
import type { EventItem } from "@/lib/api/events";
import { cn } from "@/lib/utils";
import { toneForEvent } from "./eventColors";

export interface ListViewProps {
  events: EventItem[];
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectEvent: (ev: EventItem) => void;
}

export function ListView({
  events,
  selectedEventId,
  subgroupNames,
  onSelectEvent,
}: ListViewProps) {
  // Group events by date
  const grouped = React.useMemo(() => {
    const groups = new Map<string, EventItem[]>();
    for (const ev of events) {
      const day = startOfDay(parseISO(ev.starts_at));
      const key = day.toISOString();
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key)!.push(ev);
    }

    // Sort by date and within each day by start time
    const sorted: [string, EventItem[]][] = [];
    for (const [date, items] of groups) {
      items.sort(
        (a, b) =>
          parseISO(a.starts_at).getTime() - parseISO(b.starts_at).getTime(),
      );
      sorted.push([date, items]);
    }
    sorted.sort((a, b) => a[0].localeCompare(b[0]));
    return sorted;
  }, [events]);

  if (grouped.length === 0) {
    return (
      <div className="p-6 text-center">
        <p className="text-sm text-muted">No events scheduled</p>
      </div>
    );
  }

  return (
    <div className="flex max-h-full w-full flex-col overflow-y-auto">
      {grouped.map(([dateKey, dayEvents]) => {
        const date = new Date(dateKey);
        const isToday = isSameDay(date, new Date());

        return (
          <section key={dateKey} className="mb-4">
            <h3
              className={cn(
                "mb-1.5 px-3 text-sm font-semibold",
                isToday ? "text-accent" : "text-muted",
              )}
            >
              {format(date, "EEEE, MMMM d")}
            </h3>
            <ul className="flex flex-col gap-1">
              {dayEvents.map((ev) => {
                const isSelected = selectedEventId === ev.id;
                const tone = toneForEvent(ev, subgroupNames);
                const startTime = format(parseISO(ev.starts_at), "h:mm a");
                const endTime = format(parseISO(ev.ends_at), "h:mm a");

                return (
                  <li key={ev.id}>
                    <button
                      type="button"
                      onClick={() => onSelectEvent(ev)}
                      style={{ borderLeftColor: tone.solid }}
                      className={cn(
                        "flex min-h-11 w-full flex-col justify-center border-l-4 px-3 py-2 text-left transition-colors hover:bg-surface focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent",
                        isSelected ? "bg-surface" : "bg-transparent",
                      )}
                    >
                      <span className="w-full truncate text-sm font-semibold">
                        {ev.title}
                      </span>
                      <span className="text-sm text-muted">
                        {ev.is_all_day
                          ? "All day"
                          : `${startTime} – ${endTime}`}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

export default ListView;
