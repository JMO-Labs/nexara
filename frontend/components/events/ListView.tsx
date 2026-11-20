"use client";
/**
 * @file components/events/ListView.tsx
 * @brief List view grouped by month (sticky muted headings) then date. Each
 *        event is a glass ListRow with a group colour dot and friendly time.
 */
import * as React from "react";
import { format, parseISO, startOfDay, isSameDay } from "date-fns";
import { ListRow } from "@/components/ui/page";
import type { EventItem } from "@/lib/api/events";
import { toneForEvent } from "./eventColors";
import { formatTime } from "./formatTime";

export interface ListViewProps {
  events: EventItem[];
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectEvent: (ev: EventItem) => void;
}

/**
 * @brief Friendly "when" line for a row, e.g. "Sat, Nov 21 at 9 am".
 * @param ev event to describe
 * @return display string
 */
function whenLabel(ev: EventItem): string {
  const start = parseISO(ev.starts_at);
  const day = format(start, "EEE, MMM d");
  return ev.is_all_day ? `${day} · All day` : `${day} at ${formatTime(start)}`;
}

/**
 * @brief Month-grouped event list.
 * @param props see ListViewProps
 * @return list element
 */
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

  const months: [string, [string, EventItem[]][]][] = [];
  for (const g of grouped) {
    const label = format(new Date(g[0]), "MMMM yyyy");
    const last = months[months.length - 1];
    if (last && last[0] === label) last[1].push(g);
    else months.push([label, [g]]);
  }

  return (
    <div className="flex max-h-full w-full flex-col overflow-y-auto">
      {months.map(([label, days]) => (
        <section key={label} aria-label={label} className="mb-2 last:mb-0">
          <h2 className="sticky top-0 z-10 mb-1 px-1 py-2 text-sm font-medium text-muted">
            {label}
          </h2>
          {days.map(([dateKey, dayEvents]) => {
            const date = new Date(dateKey);
            const isToday = isSameDay(date, new Date());

            return (
              <section key={dateKey} className="mb-3 last:mb-0">
                <h3
                  className={`mb-1.5 px-1 text-sm font-medium ${isToday ? "text-ink" : "text-muted"}`}
                >
                  {format(date, "EEE, MMM d")}
                </h3>
                <ul className="flex flex-col gap-2">
                  {dayEvents.map((ev) => {
                    const tone = toneForEvent(ev, subgroupNames);
                    const going = ev.rsvp_counts?.attending ?? 0;
                    return (
                      <li key={ev.id}>
                        <ListRow
                          onClick={() => onSelectEvent(ev)}
                          selected={selectedEventId === ev.id}
                          className="py-2.5"
                        >
                          <span
                            aria-hidden="true"
                            className="size-2.5 shrink-0 rounded-full"
                            style={{ backgroundColor: tone.solid }}
                          />
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-semibold">
                              {ev.title}
                            </span>
                            <span className="block truncate text-xs text-muted">
                              {whenLabel(ev)}
                              {ev.location ? ` · ${ev.location}` : ""}
                            </span>
                          </span>
                          {going > 0 && (
                            <span className="shrink-0 text-xs font-semibold text-muted">
                              {going} going
                            </span>
                          )}
                        </ListRow>
                      </li>
                    );
                  })}
                </ul>
              </section>
            );
          })}
        </section>
      ))}
    </div>
  );
}

export default ListView;
