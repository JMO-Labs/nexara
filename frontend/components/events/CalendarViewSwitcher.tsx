"use client";
/**
 * @file components/events/CalendarViewSwitcher.tsx
 * @brief Month/Week/Day/List segmented control (ink active pill).
 */
import * as React from "react";
import { Segmented } from "@/components/ui/page";

export type CalendarView = "month" | "week" | "day" | "list";

export interface CalendarViewSwitcherProps {
  value: CalendarView;
  onChange: (view: CalendarView) => void;
}

export const VIEWS = ["month", "week", "day", "list"] as const;

const OPTIONS = [
  { value: "month", label: "Month" },
  { value: "week", label: "Week" },
  { value: "day", label: "Day" },
  { value: "list", label: "List" },
] as const satisfies readonly { value: CalendarView; label: string }[];

/**
 * @brief View switcher built on the Segmented primitive.
 * @param props current value and change handler
 * @return radiogroup element
 */
export function CalendarViewSwitcher({
  value,
  onChange,
}: CalendarViewSwitcherProps) {
  return (
    <Segmented<CalendarView>
      options={[...OPTIONS]}
      value={value}
      onChange={onChange}
      label="Calendar view"
    />
  );
}

export default CalendarViewSwitcher;
