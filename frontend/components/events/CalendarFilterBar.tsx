"use client";
/**
 * @file components/events/CalendarFilterBar.tsx
 * @brief Glass toolbar above the calendar: prev / Today / next + month
 *        label, view switcher and calendar filter (popover on desktop,
 *        bottom drawer on phone).
 */
import * as React from "react";
import { addMonths, format, subMonths } from "date-fns";
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

  return (
    <Toolbar>
      <div className="flex items-center gap-1">
        <IconButton
          variant="ghost"
          size="sm"
          aria-label="Previous month"
          onClick={() => onMonthChange(subMonths(month, 1))}
        >
          <ChevronLeft className="size-4" />
        </IconButton>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onMonthChange(new Date())}
        >
          Today
        </Button>
        <IconButton
          variant="ghost"
          size="sm"
          aria-label="Next month"
          onClick={() => onMonthChange(addMonths(month, 1))}
        >
          <ChevronRight className="size-4" />
        </IconButton>
      </div>
      <h2 className="px-2 text-base font-semibold text-ink">
        {format(month, "MMMM yyyy")}
      </h2>

      <div className="flex flex-wrap items-center gap-2 md:ml-auto">
        <CalendarViewSwitcher value={view} onChange={onViewChange} />
        <span className="text-sm font-semibold text-muted">Calendars</span>
        <div className="hidden md:block">
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="secondary" size="sm" className="gap-2">
                <span className="flex gap-1">
                  {swatches.map((o) => (
                    <Swatch key={o.id} color={o.color} />
                  ))}
                </span>
                {summarize(selected.length, allOptions.length)}
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
        <div className="md:hidden">
          <Button
            variant="secondary"
            size="sm"
            className="min-h-11 gap-2"
            onClick={() => setDrawerOpen(true)}
          >
            <Filter className="size-4" aria-hidden />
            Filters
          </Button>
          <Drawer
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            title="Filters"
            side="bottom"
          >
            {picker}
          </Drawer>
        </div>
      </div>
    </Toolbar>
  );
}

export default CalendarFilterBar;
