"use client";
/**
 * @file components/calendar/CalendarWidget.tsx
 * @brief Compact month calendar; clicking a day expands its events inline.
 */
import * as React from "react";
import {
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  parseISO,
  startOfDay,
  startOfMonth,
  startOfWeek,
} from "date-fns";
import { cn } from "@/lib/utils";
import type { EventItem } from "@/lib/api/events";

export interface CalendarWidgetProps {
  events: EventItem[];
  month: Date;
}

function onDay(events: EventItem[], day: Date): EventItem[] {
  return events.filter((e) => {
    const s = startOfDay(parseISO(e.starts_at));
    const en = startOfDay(parseISO(e.ends_at));
    return day >= s && day <= en;
  });
}

/**
 * @brief Month grid of toggle buttons with an inline expanded day list.
 * @param props see CalendarWidgetProps
 * @return calendar element
 */
export function CalendarWidget({ events, month }: CalendarWidgetProps) {
  const [open, setOpen] = React.useState<Date | null>(null);
  const days = eachDayOfInterval({
    start: startOfWeek(startOfMonth(month)),
    end: endOfWeek(endOfMonth(month)),
  });
  const panelId = React.useId();
  const dayEvents = open ? onDay(events, open) : [];

  return (
    <div className="w-full">
      <h2 className="mb-2 text-base font-black">
        {format(month, "MMMM yyyy")}
      </h2>
      <div className="grid grid-cols-7 gap-0.5">
        {days.map((d) => {
          const expanded = !!open && isSameDay(open, d);
          const has = onDay(events, d).length > 0;
          return (
            <button
              key={d.toISOString()}
              type="button"
              aria-label={format(d, "EEEE, MMMM d")}
              aria-expanded={expanded}
              aria-controls={expanded ? panelId : undefined}
              onClick={() => setOpen(expanded ? null : d)}
              className={cn(
                "relative min-h-11 rounded-lg text-xs font-semibold outline-none hover:bg-ink/10 focus-visible:outline-2 focus-visible:outline-accent",
                !isSameMonth(d, month) && "opacity-60",
                expanded && "bg-accent text-surface-strong",
              )}
            >
              {format(d, "d")}
              {has && (
                <span
                  aria-hidden="true"
                  className="absolute bottom-1 left-1/2 size-1 -translate-x-1/2 rounded-full bg-current"
                />
              )}
            </button>
          );
        })}
      </div>
      {open && (
        <div id={panelId} className="mt-3 rounded-2xl bg-surface p-3">
          <p className="mb-1 text-sm font-semibold">
            {format(open, "EEEE, MMM d")}
          </p>
          {dayEvents.length === 0 ? (
            <p className="text-xs">No events</p>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {dayEvents.map((e) => (
                <li key={e.id} className="text-sm font-semibold">
                  {e.title}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default CalendarWidget;
