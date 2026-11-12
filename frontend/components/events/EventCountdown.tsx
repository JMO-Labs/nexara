"use client";
/**
 * @file components/events/EventCountdown.tsx
 * @brief Live countdown widget: time until event, large numerals with unit
 * labels below. Updates every 30s via useEventCountdown.
 */
import * as React from "react";
import { useEventCountdown } from "@/hooks/useEventCountdown";
import type { EventItem } from "@/lib/api/events";

/**
 * @brief Countdown to an event start.
 * @param event event to count down to
 * @return countdown block
 */
export function EventCountdown({ event }: { event: EventItem }) {
  const { days, hours, minutes } = useEventCountdown(event);

  const parts: Array<{ value: number; unit: string }> = [];
  if (days > 0) parts.push({ value: days, unit: "days" });
  if (days > 0 || hours > 0) parts.push({ value: hours, unit: "hours" });
  parts.push({ value: minutes, unit: "min" });

  return (
    <div className="border-y border-current/15 px-4 py-4 text-center">
      <p className="mb-3 text-sm font-semibold">{event.title}</p>
      <div className="flex items-end justify-center gap-3">
        {parts.map((part, idx) => (
          <div key={`${part.unit}-${idx}`} className="text-center">
            <div className="text-5xl leading-none font-black tabular-nums">
              {part.value}
            </div>
            <div className="mt-1 text-xs text-muted">{part.unit}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
