"use client";
/**
 * @file components/events/CalendarFilterBar.tsx
 * @brief Glass toolbar above the calendar: prev / Today / next + period
 *        title, view switcher and calendar filter (popover on desktop,
 *        bottom drawer on phone). Prev/next/Today step by month unless the
 *        page supplies onStep / onToday (week and day views).
 */
import * as React from "react";
import { addMonths, format } from "date-fns";
import { ChevronDown, ChevronLeft, ChevronRight, Filter } from "lucide-react";
import {
  Button,
  Drawer,
  IconButton,
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui";
import { Toolbar } from "@/components/ui/page";
import type { Calendar } from "@/lib/api/calendars";
import {
  CalendarViewSwitcher,
  type CalendarView,
} from "./CalendarViewSwitcher";
import { CalendarPicker, Swatch } from "./calendar-filter-bar/CalendarPicker";
import { buildGroups, summarize } from "./calendar-filter-bar/groups";
import type { CalendarSourceId } from "./calendar-filter-bar/groups";

export { buildGroups };
export type { CalendarSourceId };

export interface CalendarFilterBarProps {
  month: Date;
  onMonthChange: (m: Date) => void;
  selected: CalendarSourceId[];
  onSelectedChange: (ids: CalendarSourceId[]) => void;
  calendars: Calendar[];
  view: CalendarView;
  onViewChange: (v: CalendarView) => void;
  /** Toolbar title; defaults to the month and year. */
  title?: string;
  /** Period name used in the prev/next labels. */
  unit?: "month" | "week" | "day";
  /** Step prev (-1) / next (+1); defaults to stepping the month. */
  onStep?: (dir: -1 | 1) => void;
  /** Jump to today; defaults to the current month. */
  onToday?: () => void;
}

/**
 * @brief Calendar toolbar.
 * @param props see CalendarFilterBarProps
 * @return toolbar element
 */
export function CalendarFilterBar({
  month,
  onMonthChange,
  selected,
  onSelectedChange,
  calendars,
  view,
  onViewChange,
  title,
  unit = "month",
  onStep,
  onToday,
}: CalendarFilterBarProps) {
  const groups = React.useMemo(() => buildGroups(calendars), [calendars]);
  const allOptions = React.useMemo(
    () => groups.flatMap((g) => g.options),
    [groups],
  );
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const swatches = allOptions
    .filter((o) => selected.includes(o.id))
    .slice(0, 4);
  const picker = (
    <CalendarPicker
      groups={groups}
      selected={selected}
      onSelectedChange={onSelectedChange}
    />
  );

  const summary = summarize(selected.length, allOptions.length);

  return (
    <Toolbar>
      <div className="flex items-center gap-1">
        <IconButton
          variant="glass"
          size="sm"
          aria-label={`Previous ${unit}`}
          onClick={() =>
            onStep ? onStep(-1) : onMonthChange(addMonths(month, -1))
          }
        >
          <ChevronLeft className="size-4" />
        </IconButton>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => (onToday ? onToday() : onMonthChange(new Date()))}
        >
          Today
        </Button>
        <IconButton
          variant="glass"
          size="sm"
          aria-label={`Next ${unit}`}
          onClick={() =>
            onStep ? onStep(1) : onMonthChange(addMonths(month, 1))
          }
        >
          <ChevronRight className="size-4" />
        </IconButton>
      </div>
      <h2 className="min-w-0 truncate px-2 text-base font-semibold text-ink">
        {title ?? format(month, "MMMM yyyy")}
      </h2>

      <div className="order-last flex w-full items-center gap-2 md:order-none md:ml-auto md:w-auto">
        <div className="w-full overflow-x-auto md:w-auto [&>*]:w-full md:[&>*]:w-auto">
          <CalendarViewSwitcher value={view} onChange={onViewChange} />
        </div>
        <div className="hidden md:block">
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="glass"
                size="sm"
                className="gap-2"
                aria-label={`Calendars, ${summary}`}
              >
                <span className="flex gap-1">
                  {swatches.map((o) => (
                    <Swatch key={o.id} color={o.color} />
                  ))}
                </span>
                {summary}
                <ChevronDown className="size-3.5" aria-hidden />
              </Button>
            </PopoverTrigger>
            <PopoverContent
              align="end"
              className="max-h-[420px] w-72 overflow-y-auto p-2"
            >
              {picker}
            </PopoverContent>
          </Popover>
        </div>
      </div>
      <div className="ml-auto md:hidden">
        <IconButton
          variant="glass"
          size="md"
          aria-label="Filters"
          onClick={() => setDrawerOpen(true)}
        >
          <Filter className="size-4" aria-hidden />
        </IconButton>
        <Drawer
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          title="Filters"
          side="bottom"
        >
          {picker}
        </Drawer>
      </div>
    </Toolbar>
  );
}

export default CalendarFilterBar;
