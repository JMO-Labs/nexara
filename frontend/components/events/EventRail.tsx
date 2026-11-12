"use client";
/**
 * @file components/events/EventRail.tsx
 * @brief Right-side rail for /app/events. Renders the visible events sorted
 *        ascending and grouped by day, with a colored bar per subgroup.
 *        Selecting a row syncs with the calendar + detail panel.
 */
import * as React from "react";
import { format, isSameDay, parseISO, startOfDay } from "date-fns";
import { EmptyState } from "@/components/ui";
import { cn } from "@/lib/utils";
import type { EventItem } from "@/lib/api/events";
import { toneForEvent } from "./eventColors";

export interface EventRailProps {
  events: EventItem[];
  selectedDay: Date | null;
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectEvent: (ev: EventItem) => void;
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
      className="h-full overflow-y-auto px-3 py-2 [scrollbar-gutter:stable]"
    >
      {groups.map(([key, day, items]) => {
        const isSelectedDay =
          selectedDay && isSameDay(startOfDay(day), startOfDay(selectedDay));
        return (
          <section key={key} data-day={key} className="mb-4 scroll-mt-2">
            <h3
              className={cn(
                "bg-surface sticky top-0 z-[1] mb-2 flex items-baseline gap-2 border-b border-ink/10 py-1 text-base font-semibold tabular-nums",
                isSelectedDay ? "text-accent" : "text-ink",
              )}
            >
              {format(day, "d")}
              <span className="text-muted text-sm font-normal">
                {format(day, "EEE, MMM")}
              </span>
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
                      className="grid min-h-11 w-full grid-cols-[4px_1fr] gap-3 rounded-xl px-2 py-2 text-left transition-colors outline-none hover:bg-[var(--tone-soft)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                      style={
                        {
                          "--tone-soft": tone.soft,
                          backgroundColor: selected ? tone.soft : undefined,
                        } as React.CSSProperties
                      }
                    >
                      <span
                        aria-hidden
                        className="rounded-sm"
                        style={{ backgroundColor: tone.solid }}
                      />
                      <span className="min-w-0">
                        <span className="text-muted block text-xs tabular-nums">
                          {ev.is_all_day
                            ? "All day"
                            : `${format(parseISO(ev.starts_at), "h:mm a")} to ${format(parseISO(ev.ends_at), "h:mm a")}`}
                          {ev.location ? `, ${ev.location}` : ""}
                        </span>
                        <span className="text-ink line-clamp-2 text-sm font-semibold">
                          {ev.title}
                        </span>
                        <span
                          className="mt-0.5 block text-xs font-semibold"
                          style={{ color: tone.onSoft }}
                        >
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
