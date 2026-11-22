"use client";
/**
 * @file components/events/EventRail.tsx
 * @brief Right-side rail for /app/events. Renders the visible events sorted
 *        ascending and grouped by day, with a colour dot per subgroup.
 *        Selecting a row syncs with the calendar + detail panel.
 */
import * as React from "react";
import { format, isSameDay, parseISO, startOfDay } from "date-fns";
import { CalendarDays } from "lucide-react";
import { EmptyState } from "@/components/ui";
import { cn } from "@/lib/utils";
import type { EventItem } from "@/lib/api/events";
import { toneForEvent } from "./eventColors";
import { formatTime } from "./formatTime";
import { EventTitle } from "./EventTitle";

export interface EventRailProps {
  events: EventItem[];
  selectedDay: Date | null;
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectEvent: (ev: EventItem) => void;
  /** Optional action (e.g. "New event") shown in the empty state. */
  emptyAction?: React.ReactNode;
}

function dayKey(iso: string): string {
  return format(parseISO(iso), "yyyy-MM-dd");
}

/**
 * @brief Day-grouped event list.
 * @param props see EventRailProps
 * @return rail element
 */
export function EventRail({
  events,
  selectedDay,
  selectedEventId,
  subgroupNames,
  onSelectEvent,
  emptyAction,
}: EventRailProps) {
  const sorted = React.useMemo(
    () =>
      [...events].sort(
        (a, b) =>
          parseISO(a.starts_at).getTime() - parseISO(b.starts_at).getTime(),
      ),
    [events],
  );

  const groups = React.useMemo<[string, Date, EventItem[]][]>(() => {
    if (selectedDay) {
      const k = format(selectedDay, "yyyy-MM-dd");
      return sorted.length ? [[k, selectedDay, sorted]] : [];
    }
    const map = new Map<string, EventItem[]>();
    for (const ev of sorted) {
      const k = dayKey(ev.starts_at);
      const arr = map.get(k) ?? [];
      arr.push(ev);
      map.set(k, arr);
    }
    return Array.from(map.entries()).map(([k, items]) => [
      k,
      parseISO(items[0].starts_at),
      items,
    ]);
  }, [sorted, selectedDay]);

  const containerRef = React.useRef<HTMLDivElement | null>(null);
  React.useEffect(() => {
    if (!selectedDay || !containerRef.current) return;
    const k = format(selectedDay, "yyyy-MM-dd");
    const el = containerRef.current.querySelector<HTMLElement>(
      `[data-day="${k}"]`,
    );
    el?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }, [selectedDay]);

  if (groups.length === 0) {
    return (
      <div className="p-4">
        <EmptyState
          compact
          icon={CalendarDays}
          action={emptyAction}
          title={
            selectedDay
              ? `No events on ${format(selectedDay, "MMM d")}`
              : "Nothing this month"
          }
          description={
            selectedDay
              ? "Pick another day or clear the selection to see the full month."
              : "Switch months or clear filters to see more events."
          }
        />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="h-full overflow-y-auto px-2 py-1 [scrollbar-gutter:stable]"
    >
      {groups.map(([key, day, items]) => {
        const isSelectedDay =
          selectedDay && isSameDay(startOfDay(day), startOfDay(selectedDay));
        return (
          <section
            key={key}
            data-day={key}
            className="mb-3 scroll-mt-2 last:mb-0"
          >
            <h3
              className={cn(
                "sticky top-0 z-[1] mb-1.5 px-1 py-1 text-sm font-medium",
                isSelectedDay ? "text-ink" : "text-muted",
              )}
            >
              {format(day, "EEE, MMM d")}
            </h3>
            <ul className="flex flex-col gap-1">
              {items.map((ev) => {
                const tone = toneForEvent(ev, subgroupNames);
                const selected = selectedEventId === ev.id;
                return (
                  <li key={ev.id}>
                    <button
                      type="button"
                      onClick={() => onSelectEvent(ev)}
                      aria-pressed={selected}
                      className={cn(
                        "glass-item flex min-h-11 w-full items-start gap-3 rounded-[22px] px-3 py-2 text-left transition-colors outline-none hover:bg-white/30 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
                        selected && "ring-2 ring-ink",
                      )}
                    >
                      <span
                        aria-hidden="true"
                        className="mt-1.5 size-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: tone.solid }}
                      />
                      <span className="min-w-0">
                        <span className="text-muted block text-xs tabular-nums">
                          {ev.is_all_day
                            ? "All day"
                            : `${formatTime(parseISO(ev.starts_at))} to ${formatTime(parseISO(ev.ends_at))}`}
                          {ev.location ? `, ${ev.location}` : ""}
                        </span>
                        <span className="text-ink line-clamp-2 text-sm font-semibold">
                          <EventTitle ev={ev} />
                        </span>
                        <span className="mt-0.5 block text-xs font-semibold text-muted">
                          {tone.label}
                        </span>
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

export default EventRail;
