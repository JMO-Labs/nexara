"use client";
/**
 * @file components/events/CalendarViewSwitcher.tsx
 * @brief Segmented control for switching between month/week/day/list views.
 */
import * as React from "react";
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/shadcn/toggle-group";

export type CalendarView = "month" | "week" | "day" | "list";

export interface CalendarViewSwitcherProps {
  value: CalendarView;
  onChange: (view: CalendarView) => void;
}

export const VIEWS = ["month", "week", "day", "list"] as const;

/**
 * @brief View switcher built on toggle-group (single select, never empty).
 * @param props current value and change handler
 * @return switcher element
 */
export function CalendarViewSwitcher({
  value,
  onChange,
}: CalendarViewSwitcherProps) {
  return (
    <ToggleGroup
      type="single"
      value={value}
      onValueChange={(v) => v && onChange(v as CalendarView)}
      aria-label="Calendar view"
      className="mb-4 max-w-full"
    >
      {VIEWS.map((view) => (
        <ToggleGroupItem
          key={view}
          value={view}
          className="min-h-11 px-4 capitalize"
        >
          {view}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}

export default CalendarViewSwitcher;
