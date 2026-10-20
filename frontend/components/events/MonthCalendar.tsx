"use client";
/**
 * @file components/events/MonthCalendar.tsx
 * @brief Month-grid calendar with multi-day spanning event bars and per-day
 *        hover preview popovers. Mirrors Google Calendar layout: week rows,
 *        bars span consecutive days within a week and re-flow to the next
 *        week's row when an event crosses a Sunday boundary.
 */
import * as React from "react";
import {
  addMonths,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  isToday,
  parseISO,
  startOfDay,
  startOfMonth,
  startOfWeek,
  subMonths,
} from "date-fns";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { IconButton, Tooltip } from "@/components/ui";
import { cn } from "@/lib/utils";
import { toneForEvent } from "./eventColors";
import { chipStyle } from "./toneStyle";
import type { EventItem } from "@/lib/api/events";

const BRAND_TONE = toneForEvent({
  visibility: "community",
  subgroup_id: null,
  color: null,
});
const LANE_HEIGHT = 18;
const MAX_LANES_VISIBLE = 3;
const HEADER_OFFSET = 26;

interface Segment {
  event: EventItem;
  col: number; // 0-6 within the week
  span: number; // 1-7
  lane: number;
  startsHere: boolean;
  endsHere: boolean;
}

function buildWeeks(month: Date): Date[][] {
  const start = startOfWeek(startOfMonth(month), { weekStartsOn: 0 });
  const end = endOfWeek(endOfMonth(month), { weekStartsOn: 0 });
  const weeks: Date[][] = [];
  let cur = start;
  while (cur <= end) {
    const week: Date[] = [];
    for (let i = 0; i < 7; i++) {
      week.push(cur);
      cur = new Date(cur.getTime() + 86400_000);
    }
    weeks.push(week);
  }
  return weeks;
}

function eventOverlapsWeek(
  ev: EventItem,
  weekStart: Date,
  weekEnd: Date,
): boolean {
  const s = startOfDay(parseISO(ev.starts_at));
  const e = startOfDay(parseISO(ev.ends_at));
  return s <= weekEnd && e >= weekStart;
}

function assignLanes(events: EventItem[], week: Date[]): Segment[] {
  const weekStart = week[0];
  const weekEnd = week[6];
  const lanes: Date[] = []; // per-lane: last-occupied col-end-date
  const segs: Segment[] = [];
  const sorted = [...events]
    .filter((e) => eventOverlapsWeek(e, weekStart, weekEnd))
    .sort(
      (a, b) =>
        parseISO(a.starts_at).getTime() - parseISO(b.starts_at).getTime(),
    );
  for (const ev of sorted) {
    const evStart = startOfDay(parseISO(ev.starts_at));
    const evEnd = startOfDay(parseISO(ev.ends_at));
    const segStart = evStart < weekStart ? weekStart : evStart;
    const segEnd = evEnd > weekEnd ? weekEnd : evEnd;
    const col = Math.round(
      (segStart.getTime() - weekStart.getTime()) / 86400_000,
    );
    const span =
      Math.round((segEnd.getTime() - segStart.getTime()) / 86400_000) + 1;
    let lane = lanes.findIndex((d) => d < segStart);
    if (lane === -1) {
      lane = lanes.length;
      lanes.push(segEnd);
    } else {
      lanes[lane] = segEnd;
    }
    segs.push({
      event: ev,
      col,
      span,
      lane,
      startsHere: isSameDay(evStart, segStart),
      endsHere: isSameDay(evEnd, segEnd),
    });
  }
  return segs;
}

function eventsOnDay(events: EventItem[], day: Date): EventItem[] {
  return events.filter((ev) => {
    const s = startOfDay(parseISO(ev.starts_at));
    const e = startOfDay(parseISO(ev.ends_at));
    return day >= s && day <= e;
  });
}

function DayPreview({ day, events }: { day: Date; events: EventItem[] }) {
  return (
    <div className="max-h-70 max-w-70 overflow-y-auto p-1">
      <p className="mb-1 text-sm font-semibold">{format(day, "EEEE, MMM d")}</p>
      {events.length === 0 ? (
        <p className="text-xs">No events</p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {events.map((ev) => (
            <li key={ev.id}>
              <span className="block text-xs opacity-80">
                {ev.is_all_day
                  ? "All day"
                  : format(parseISO(ev.starts_at), "p")}
                {ev.location ? ` · ${ev.location}` : ""}
              </span>
              <span className="block text-sm font-semibold">{ev.title}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export interface MonthCalendarProps {
  events: EventItem[];
  month: Date;
  onMonthChange: (m: Date) => void;
}

/**
 * @brief Compact month grid with navigation and per-day hover preview.
 * @param props see MonthCalendarProps
 * @return calendar element
 */
export function MonthCalendar({
  events,
  month,
  onMonthChange,
}: MonthCalendarProps) {
  const weeks = React.useMemo(() => buildWeeks(month), [month]);
  const weekSegments = React.useMemo(
    () => weeks.map((w) => assignLanes(events, w)),
    [weeks, events],
  );

  return (
    <div className="w-full">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-base font-black">{format(month, "MMMM yyyy")}</h2>
        <div className="flex items-center gap-1">
          <IconButton
            size="sm"
            variant="ghost"
            aria-label="Previous month"
            onClick={() => onMonthChange(subMonths(month, 1))}
          >
            <ChevronLeft className="size-4" aria-hidden="true" />
          </IconButton>
          <IconButton
            size="sm"
            variant="ghost"
            aria-label="Today"
            className="w-auto px-3 text-xs"
            onClick={() => onMonthChange(new Date())}
          >
            Today
          </IconButton>
          <IconButton
            size="sm"
            variant="ghost"
            aria-label="Next month"
            onClick={() => onMonthChange(addMonths(month, 1))}
          >
            <ChevronRight className="size-4" aria-hidden="true" />
          </IconButton>
        </div>
      </div>

      <div className="mb-1 grid grid-cols-7" aria-hidden="true">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
          <span key={d} className="text-center text-xs text-muted">
            {d}
          </span>
        ))}
      </div>

      <div className="overflow-hidden rounded-2xl bg-surface">
        {weeks.map((week, wi) => {
          const segs = weekSegments[wi];
          const maxLane = segs.reduce((m, s) => Math.max(m, s.lane + 1), 0);
          const visibleLanes = Math.min(maxLane, MAX_LANES_VISIBLE);
          const rowHeight =
            HEADER_OFFSET +
            visibleLanes * LANE_HEIGHT +
            (maxLane > MAX_LANES_VISIBLE ? 16 : 4);

          return (
            <div
              key={wi}
              className={cn(
                "relative grid grid-cols-7",
                wi > 0 && "border-t border-ink/15",
              )}
              style={{ minHeight: rowHeight }}
            >
              {week.map((day, di) => {
                const inMonth = isSameMonth(day, month);
                const today = isToday(day);
                return (
                  <Tooltip
                    key={day.toISOString()}
                    content={
                      <DayPreview day={day} events={eventsOnDay(events, day)} />
                    }
                  >
                    <div
                      tabIndex={0}
                      aria-label={format(day, "EEEE, MMMM d")}
                      className={cn(
                        "p-1 outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent",
                        di > 0 && "border-l border-ink/15",
                        !inMonth && "opacity-60",
                      )}
                      style={{ minHeight: rowHeight }}
                    >
                      <span
                        className={cn(
                          "inline-flex size-6 items-center justify-center rounded-full text-xs",
                          today
                            ? "bg-accent font-black text-surface-strong"
                            : "font-semibold text-ink",
                        )}
                      >
                        {format(day, "d")}
                      </span>
                    </div>
                  </Tooltip>
                );
              })}

              {/* Event bar overlay */}
              <div
                className="pointer-events-none absolute inset-x-0 grid grid-cols-7"
                style={{ top: HEADER_OFFSET }}
              >
                {segs
                  .filter((s) => s.lane < MAX_LANES_VISIBLE)
                  .map((s, i) => (
                    <div
                      key={`${s.event.id}-${i}`}
                      title={s.event.title}
                      className={cn(
                        "pointer-events-auto mx-px truncate px-1.5 text-[11px] font-semibold",
                        s.startsHere && "rounded-l",
                        s.endsHere && "rounded-r",
                      )}
                      style={{
                        gridColumn: `${s.col + 1} / span ${s.span}`,
                        gridRow: 1,
                        transform: `translateY(${s.lane * LANE_HEIGHT}px)`,
                        height: LANE_HEIGHT - 3,
                        lineHeight: `${LANE_HEIGHT - 3}px`,
                        ...chipStyle(BRAND_TONE, true),
                      }}
                    >
                      {s.startsHere ? s.event.title : " "}
                    </div>
                  ))}
                {segs.some((s) => s.lane >= MAX_LANES_VISIBLE) && (
                  <div
                    className="pointer-events-none px-1 text-[11px] text-muted"
                    style={{
                      gridColumn: "1 / span 7",
                      gridRow: 1,
                      transform: `translateY(${MAX_LANES_VISIBLE * LANE_HEIGHT}px)`,
                    }}
                  >
                    + more
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default MonthCalendar;
