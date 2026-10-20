"use client";
/**
 * @file components/events/DayView.tsx
 * @brief Single-day calendar view. Hour ticks on left, events in single column.
 *        Multi-event overlap allowed with left-edge positioning.
 */
import * as React from "react";
import { format, isToday as isTodayFn, parseISO } from "date-fns";
import type { EventItem } from "@/lib/api/events";
import { assignTimeLanes } from "@/lib/events/lanes";
import { cn } from "@/lib/utils";
import { toneForEvent } from "./eventColors";
import { chipStyle } from "./toneStyle";

const HOUR_HEIGHT = 48;
const LANE_HEIGHT = 20;
const HOUR_LABEL_WIDTH = 44;

export interface DayViewProps {
  day: Date;
  events: EventItem[];
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectEvent: (ev: EventItem) => void;
}

export function DayView({
  day,
  events,
  selectedEventId,
  subgroupNames,
  onSelectEvent,
}: DayViewProps) {
  // Split events into all-day and timed for this day
  const { allDay, timed } = React.useMemo(() => {
    const dayStart = new Date(day);
    dayStart.setHours(0, 0, 0, 0);
    const dayEnd = new Date(day);
    dayEnd.setHours(23, 59, 59, 999);

    const allDay: EventItem[] = [];
    const timed: EventItem[] = [];
    for (const ev of events) {
      const evStart = parseISO(ev.starts_at);
      const evEnd = parseISO(ev.ends_at);
      if (!(evStart <= dayEnd && evEnd >= dayStart)) continue;
      // Treat as all-day if flagged or if it spans the entire visible day.
      const spansFullDay =
        evStart.getTime() <= dayStart.getTime() &&
        evEnd.getTime() >= dayEnd.getTime();
      if (ev.is_all_day || spansFullDay) allDay.push(ev);
      else timed.push(ev);
    }
    return { allDay, timed };
  }, [day, events]);

  const lanes = React.useMemo(
    () => assignTimeLanes(timed, subgroupNames, HOUR_HEIGHT, LANE_HEIGHT, day),
    [timed, subgroupNames, day],
  );

  // Current-time indicator (only when day === today)
  const [now, setNow] = React.useState(() => new Date());
  React.useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);
  const isToday = isTodayFn(day);
  const nowOffset = (now.getHours() + now.getMinutes() / 60) * HOUR_HEIGHT;

  return (
    <div className="flex h-full w-full flex-col">
      {/* Day header */}
      <div
        className="mb-2 border-b border-ink/15 py-3 text-center"
        aria-current={isToday ? "date" : undefined}
      >
        <h2 className="text-xl font-black">{format(day, "EEEE")}</h2>
        <p className="text-sm text-muted">{format(day, "MMMM d, yyyy")}</p>
      </div>

      {/* All-day strip */}
      {allDay.length > 0 && (
        <div className="mb-2 flex items-start gap-2 pr-1">
          <span
            className="shrink-0 pr-2 pt-1 text-right text-[11px] font-semibold text-muted"
            style={{ width: HOUR_LABEL_WIDTH }}
          >
            All day
          </span>
          <div className="flex flex-1 flex-wrap gap-1.5">
            {allDay.map((ev) => {
              const tone = toneForEvent(ev, subgroupNames);
              return (
                <button
                  key={ev.id}
                  type="button"
                  onClick={() => onSelectEvent(ev)}
                  className="min-h-8 cursor-pointer rounded border px-2 py-1 text-xs font-semibold outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  style={{
                    ...chipStyle(tone, selectedEventId === ev.id),
                    ...(selectedEventId === ev.id
                      ? {}
                      : { borderColor: "transparent" }),
                  }}
                >
                  {ev.title}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Timeline grid */}
      <div className="relative flex min-h-0 flex-1 overflow-y-auto overflow-x-hidden rounded-2xl bg-surface">
        {/* Hour labels */}
        <div
          className="shrink-0 border-r border-ink/15 pt-0.5"
          style={{ width: HOUR_LABEL_WIDTH }}
        >
          {Array.from({ length: 24 }).map((_, hour) => (
            <div
              key={hour}
              className={cn(
                "flex items-start justify-end pr-2 text-[11px] font-semibold text-muted",
                hour < 23 && "border-b border-ink/15",
              )}
              style={{ height: HOUR_HEIGHT }}
            >
              {format(new Date().setHours(hour, 0), "h a")}
            </div>
          ))}
        </div>

        {/* Events container */}
        <div
          className="relative flex-1"
          style={{ minHeight: 24 * HOUR_HEIGHT }}
        >
          {Array.from({ length: 24 }).map((_, hour) => (
            <div
              key={hour}
              className={cn(
                "absolute inset-x-0",
                hour < 23 && "border-b border-ink/15",
              )}
              style={{ top: hour * HOUR_HEIGHT, height: HOUR_HEIGHT }}
            />
          ))}

          {/* Current-time indicator */}
          {isToday && (
            <div
              className="pointer-events-none absolute inset-x-0 z-20 h-0 border-t-2 border-ink"
              style={{ top: nowOffset }}
              aria-hidden="true"
            >
              <span className="absolute -left-1 -top-[5px] size-2 rounded-full bg-ink ring-2 ring-surface" />
            </div>
          )}

          {/* Event blocks */}
          {lanes.map((seg, idx) => {
            const isSelected = selectedEventId === seg.event.id;
            const laneWidthPct = 100 / seg.cluster;
            return (
              <div
                key={`event-${seg.event.id}-${idx}`}
                role="button"
                tabIndex={0}
                aria-label={`${seg.event.title}, ${format(parseISO(seg.event.starts_at), "p")}`}
                onClick={() => onSelectEvent(seg.event)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectEvent(seg.event);
                  }
                }}
                className="absolute z-10 box-border cursor-pointer overflow-hidden rounded border px-1.5 py-1 text-[11px] font-semibold leading-tight outline-none hover:z-[11] focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent"
                style={{
                  top: seg.topOffset,
                  left: `${seg.lane * laneWidthPct}%`,
                  width: `calc(${laneWidthPct}% - 4px)`,
                  height: seg.height,
                  ...chipStyle(seg.tone, isSelected),
                  ...(isSelected ? {} : { borderColor: "transparent" }),
                }}
              >
                <p className="truncate font-black">{seg.event.title}</p>
                {seg.height >= 32 && (
                  <p className="mt-px text-[11px] opacity-90">
                    {format(parseISO(seg.event.starts_at), "h:mm a")}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default DayView;
