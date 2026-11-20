"use client";
/**
 * @file components/events/MonthCalendarLarge.tsx
 * @brief Page-scale monthly calendar. Tall day cells, multi-day spanning event
 *        bars colored per subgroup, day-click selects a date, bar-click
 *        selects an event. Arrow keys move day focus. On phones the grid shows
 *        dots and the selected day's events are listed below.
 */
import * as React from "react";
import {
  addDays,
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
} from "date-fns";
import type { EventItem } from "@/lib/api/events";
import { assignLanes } from "@/lib/events/lanes";
import { EmptyState } from "@/components/ui";
import { CalendarDays } from "lucide-react";
import { cn } from "@/lib/utils";
import { toneForEvent } from "./eventColors";
import { formatTime } from "./formatTime";
import { chipStyle, TODAY_PILL } from "./toneStyle";

const LANE_HEIGHT = 22;
const HEADER_OFFSET = 34;
const CELL_MIN_HEIGHT = 104;
const OVERFLOW_RESERVE = 18;
// Lanes that can stack within a day cell without overflowing it vertically.
const MAX_LANES_VISIBLE = Math.max(
  1,
  Math.floor(
    (CELL_MIN_HEIGHT - HEADER_OFFSET - OVERFLOW_RESERVE) / LANE_HEIGHT,
  ),
);
const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const ARROW_DELTA: Record<string, number> = {
  ArrowLeft: -1,
  ArrowRight: 1,
  ArrowUp: -7,
  ArrowDown: 7,
};

function buildWeeks(month: Date): Date[][] {
  const end = endOfWeek(endOfMonth(month), { weekStartsOn: 0 });
  const weeks: Date[][] = [];
  let cur = startOfWeek(startOfMonth(month), { weekStartsOn: 0 });
  while (cur <= end) {
    weeks.push(Array.from({ length: 7 }, (_, i) => addDays(cur, i)));
    cur = addDays(cur, 7);
  }
  return weeks;
}

function eventsOnDay(events: EventItem[], day: Date): EventItem[] {
  const d = startOfDay(day);
  return events.filter(
    (ev) =>
      startOfDay(parseISO(ev.starts_at)) <= d &&
      startOfDay(parseISO(ev.ends_at)) >= d,
  );
}

export interface MonthCalendarLargeProps {
  events: EventItem[];
  month: Date;
  selectedDay: Date | null;
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectDay: (d: Date) => void;
  onSelectEvent: (ev: EventItem) => void;
}

/**
 * @brief Large month grid.
 * @param props see MonthCalendarLargeProps
 * @return calendar element
 */
export function MonthCalendarLarge({
  events,
  month,
  selectedDay,
  selectedEventId,
  subgroupNames,
  onSelectDay,
  onSelectEvent,
}: MonthCalendarLargeProps) {
  const weeks = React.useMemo(() => buildWeeks(month), [month]);
  const weekSegments = React.useMemo(
    () => weeks.map((w) => assignLanes(events, w, subgroupNames)),
    [weeks, events, subgroupNames],
  );
  const gridRef = React.useRef<HTMLDivElement>(null);
  // Roving tabindex: selected day, else today, else first of month.
  const flat = weeks.flat();
  const focusDay =
    (selectedDay && flat.find((d) => isSameDay(d, selectedDay))) ||
    flat.find((d) => isToday(d) && isSameMonth(d, month)) ||
    startOfMonth(month);

  const onCellKey = (e: React.KeyboardEvent, day: Date) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelectDay(day);
      return;
    }
    const delta = ARROW_DELTA[e.key];
    if (delta === undefined) return;
    e.preventDefault();
    const next = addDays(day, delta);
    gridRef.current
      ?.querySelector<HTMLElement>(`[data-day="${format(next, "yyyy-MM-dd")}"]`)
      ?.focus();
  };

  const dayEvents = selectedDay ? eventsOnDay(events, selectedDay) : [];

  return (
    <div className="w-full">
      <div className="mb-1 grid grid-cols-7 gap-1" aria-hidden="true">
        {DAY_NAMES.map((d) => (
          <span
            key={d}
            className="py-1 text-center text-xs font-medium text-muted"
          >
            {d}
          </span>
        ))}
      </div>

      <div
        ref={gridRef}
        role="grid"
        aria-label={format(month, "MMMM yyyy")}
        className="flex flex-col gap-1"
      >
        {weeks.map((week, wi) => {
          const segs = weekSegments[wi];
          const overflowByDay = week.map(
            (_d, di) =>
              segs.filter(
                (s) =>
                  s.lane >= MAX_LANES_VISIBLE &&
                  di >= s.col &&
                  di < s.col + s.span,
              ).length,
          );
          return (
            <div
              key={wi}
              role="row"
              className={cn("relative grid grid-cols-7 gap-1 sm:min-h-[104px]")}
            >
              {week.map((day, di) => {
                const inMonth = isSameMonth(day, month);
                const today = isToday(day);
                const selected = !!selectedDay && isSameDay(day, selectedDay);
                const dayOverflow = overflowByDay[di];
                const dots = eventsOnDay(events, day).slice(0, 3);
                return (
                  <div
                    key={day.toISOString()}
                    role="gridcell"
                    aria-selected={selected}
                    aria-label={format(day, "EEEE, MMMM d")}
                    data-day={format(day, "yyyy-MM-dd")}
                    tabIndex={isSameDay(day, focusDay) ? 0 : -1}
                    onClick={() => onSelectDay(day)}
                    onKeyDown={(e) => onCellKey(e, day)}
                    className={cn(
                      "glass-item relative min-h-14 cursor-pointer rounded-[18px] px-1 pt-1 sm:px-2 sm:pt-1.5",
                      "outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent",
                      selected && "ring-2 ring-ink",
                      !inMonth && "opacity-60",
                      "motion-safe:transition-colors hover:ring-1 hover:ring-ink/30",
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span
                        className={cn(
                          "inline-flex h-7 min-w-7 items-center justify-center rounded-full px-1.5 text-sm tabular-nums",
                          today ? TODAY_PILL : "font-semibold text-ink",
                        )}
                      >
                        {format(day, "d")}
                      </span>
                      {day.getDate() === 1 ? (
                        <span className="hidden text-xs font-medium text-muted sm:inline">
                          {format(day, "MMM")}
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-1 flex justify-center gap-1 sm:hidden">
                      {dots.map((ev) => (
                        <span
                          key={ev.id}
                          aria-hidden="true"
                          className="size-1.5 rounded-full"
                          style={{
                            backgroundColor: toneForEvent(ev, subgroupNames)
                              .solid,
                          }}
                        />
                      ))}
                    </div>
                    {dayOverflow > 0 && (
                      <span className="pointer-events-none absolute inset-x-1 bottom-0.5 hidden text-[11px] font-semibold text-muted sm:block">
                        +{dayOverflow} more
                      </span>
                    )}
                  </div>
                );
              })}

              {/* Event bar overlay (tablet and up) */}
              <div
                className="pointer-events-none absolute inset-x-0 hidden grid-cols-7 gap-1 sm:grid"
                style={{ top: HEADER_OFFSET }}
              >
                {segs
                  .filter((s) => s.lane < MAX_LANES_VISIBLE)
                  .map((s, i) => {
                    const solid =
                      selectedEventId === s.event.id || s.event.is_all_day;
                    return (
                      <div
                        key={`${s.event.id}-${i}`}
                        role="button"
                        tabIndex={0}
                        title={s.event.title}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectEvent(s.event);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            e.stopPropagation();
                            onSelectEvent(s.event);
                          }
                        }}
                        className="pointer-events-auto flex cursor-pointer items-center gap-1.5 rounded-full px-2 text-xs font-semibold outline-none focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent"
                        style={{
                          gridColumn: `${s.col + 1} / span ${s.span}`,
                          gridRow: 1,
                          transform: `translateY(${s.lane * LANE_HEIGHT}px)`,
                          height: LANE_HEIGHT - 4,
                          lineHeight: `${LANE_HEIGHT - 4}px`,
                          ...chipStyle(s.tone, solid),
                        }}
                      >
                        {s.startsHere && (
                          <span
                            aria-hidden="true"
                            className="size-2 shrink-0 rounded-full"
                            style={{ backgroundColor: s.tone.solid }}
                          />
                        )}
                        <span className="min-w-0 truncate">
                          {s.startsHere
                            ? `${s.event.is_all_day ? "" : `${formatTime(parseISO(s.event.starts_at))} · `}${s.event.title}`
                            : " "}
                        </span>
                      </div>
                    );
                  })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Phone: events for the selected day */}
      {selectedDay && (
        <div className="mt-3 sm:hidden" aria-live="polite">
          <h3 className="mb-2 text-sm font-medium text-muted">
            {format(selectedDay, "EEE, MMM d")}
          </h3>
          {dayEvents.length === 0 ? (
            <EmptyState
              compact
              icon={CalendarDays}
              title="No events this day"
            />
          ) : (
            <ul className="flex flex-col gap-2">
              {dayEvents.map((ev) => {
                const tone = toneForEvent(ev, subgroupNames);
                return (
                  <li key={ev.id}>
                    <button
                      type="button"
                      onClick={() => onSelectEvent(ev)}
                      className="glass-item flex min-h-11 w-full items-center gap-3 rounded-[22px] px-3 py-2 text-left outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
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
                        <span className="block text-xs text-muted">
                          {ev.is_all_day
                            ? "All day"
                            : formatTime(parseISO(ev.starts_at))}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default MonthCalendarLarge;
