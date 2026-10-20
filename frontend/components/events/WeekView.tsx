"use client";
/**
 * @file components/events/WeekView.tsx
 * @brief Weekly calendar grid view. 7 columns, hourly rows (48px each).
 *        Current time line (1px accent) with 6px dot. Scrolls sideways inside
 *        its own container on phones.
 *        Multi-event overlap allowed via lane assignment.
 */
import * as React from "react";
import {
  format,
  getHours,
  isToday as isTodayFn,
  parseISO,
  addDays,
} from "date-fns";
import type { EventItem } from "@/lib/api/events";
import { assignTimeLanes, type TimeLane } from "@/lib/events/lanes";
import { cn } from "@/lib/utils";
import { chipStyle } from "./toneStyle";

const HOUR_HEIGHT = 48;
const LANE_HEIGHT = 20;
const HOUR_LABEL_WIDTH = 44;

export interface WeekViewProps {
  weekStart: Date;
  events: EventItem[];
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectEvent: (ev: EventItem) => void;
}

export function WeekView({
  weekStart,
  events,
  selectedEventId,
  subgroupNames,
  onSelectEvent,
}: WeekViewProps) {
  // Build 7-day week
  const week = React.useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)),
    [weekStart],
  );

  /** Per-day lane assignment — events grouped by their start day, then time-overlap lanes within each day. */
  const lanesPerDay = React.useMemo(() => {
    const out: Array<{ day: Date; lanes: TimeLane[] }> = [];
    for (const day of week) {
      const dayStart = new Date(day);
      dayStart.setHours(0, 0, 0, 0);
      const dayEnd = new Date(day);
      dayEnd.setHours(23, 59, 59, 999);
      const dayEvents = events.filter((ev) => {
        const s = parseISO(ev.starts_at);
        const e = parseISO(ev.ends_at);
        return s <= dayEnd && e >= dayStart;
      });
      out.push({
        day,
        lanes: assignTimeLanes(
          dayEvents,
          subgroupNames,
          HOUR_HEIGHT,
          LANE_HEIGHT,
          dayStart,
        ),
      });
    }
    return out;
  }, [events, week, subgroupNames]);

  const now = new Date();
  const currentHour = getHours(now);
  const todayIndex = week.findIndex((d) => isTodayFn(d));

  return (
    <div className="flex h-full w-full flex-col overflow-x-auto">
      <div className="flex h-full min-w-[560px] flex-1 flex-col">
        {/* Day headers */}
        <div
          className="mb-2 grid px-1"
          style={{
            gridTemplateColumns: `${HOUR_LABEL_WIDTH}px repeat(7, 1fr)`,
          }}
        >
          <div />
          {week.map((day) => {
            const today = isTodayFn(day);
            return (
              <div key={day.toISOString()} className="py-1.5 text-center">
                <p className="text-xs font-semibold text-muted">
                  {format(day, "EEE")}
                </p>
                <p
                  className={cn(
                    "mx-auto mt-0.5 flex size-7 items-center justify-center rounded-full text-sm",
                    today
                      ? "bg-accent font-black text-surface-strong"
                      : "font-semibold text-ink",
                  )}
                  aria-current={today ? "date" : undefined}
                >
                  {format(day, "d")}
                </p>
              </div>
            );
          })}
        </div>

        {/* Scrollable timeline */}
        <div className="relative flex flex-1 overflow-y-auto overflow-x-hidden rounded-2xl bg-surface">
          {/* Hour label gutter */}
          <div
            className="shrink-0 border-r border-ink/15"
            style={{ width: HOUR_LABEL_WIDTH }}
          >
            {Array.from({ length: 24 }).map((_, hour) => (
              <div
                key={hour}
                className={cn(
                  "flex items-start justify-end pr-2 pt-0.5 text-[11px] font-semibold text-muted",
                  hour < 23 && "border-b border-ink/15",
                )}
                style={{ height: HOUR_HEIGHT }}
              >
                {hour === 0 ? "" : format(new Date().setHours(hour, 0), "h a")}
              </div>
            ))}
          </div>

          {/* Hour rows grid (7 day columns) */}
          <div
            className="relative grid flex-1 grid-cols-7"
            style={{ minHeight: 24 * HOUR_HEIGHT }}
          >
            {Array.from({ length: 24 }).map((_, hour) => (
              <React.Fragment key={hour}>
                {Array.from({ length: 7 }).map((_, dayIdx) => (
                  <div
                    key={`${hour}-${dayIdx}`}
                    className={cn(
                      "hover:bg-bg motion-safe:transition-colors",
                      dayIdx < 6 && "border-r border-ink/15",
                      hour < 23 && "border-b border-ink/15",
                    )}
                    style={{ height: HOUR_HEIGHT }}
                  />
                ))}
              </React.Fragment>
            ))}

            {/* Event blocks overlay: per-day, lane-aware horizontal placement */}
            {lanesPerDay.flatMap(({ lanes }, dayIdx) => {
              const dayWidthPct = 100 / 7;
              const dayLeftPct = dayIdx * dayWidthPct;
              return lanes.map((seg, segIdx) => {
                const isSelected = selectedEventId === seg.event.id;
                const laneWidthPct = dayWidthPct / seg.cluster;
                return (
                  <div
                    key={`event-${seg.event.id}-${dayIdx}-${segIdx}`}
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
                    className="absolute z-10 box-border cursor-pointer overflow-hidden text-ellipsis whitespace-nowrap rounded border px-1 py-0.5 text-[11px] font-semibold leading-tight outline-none hover:z-[11] focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent"
                    style={{
                      left: `${dayLeftPct + seg.lane * laneWidthPct}%`,
                      width: `calc(${laneWidthPct}% - 2px)`,
                      top: seg.topOffset,
                      height: seg.height,
                      ...chipStyle(seg.tone, isSelected),
                      ...(isSelected ? {} : { borderColor: "transparent" }),
                    }}
                  >
                    {seg.event.title}
                  </div>
                );
              });
            })}

            {/* Current time indicator */}
            {todayIndex !== -1 && (
              <div
                className="pointer-events-none absolute z-20 h-px bg-ink"
                style={{
                  top:
                    currentHour * HOUR_HEIGHT +
                    (now.getMinutes() / 60) * HOUR_HEIGHT,
                  left: `${(todayIndex * 100) / 7}%`,
                  width: `${100 / 7}%`,
                }}
                aria-hidden="true"
              >
                <span className="absolute -top-[2.5px] left-1 size-1.5 rounded-full bg-ink" />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default WeekView;
