"use client";
/**
 * @file components/events/EventCountdown.tsx
 * @brief Live countdown: large numerals with unit labels below. Title is
 * omitted; the host page/panel already names the event. Updates every 30s.
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
    <div
      className="flex items-end gap-5"
      aria-label={`Starts in ${parts.map((p) => `${p.value} ${p.unit}`).join(", ")}`}
    >
      {parts.map((part, idx) => (
        <div key={`${part.unit}-${idx}`}>
          <div className="text-4xl leading-none font-medium tracking-tight tabular-nums">
            {part.value}
          </div>
          <div className="mt-1 text-xs text-muted">{part.unit}</div>
        </div>
      ))}
    </div>
  );
}
