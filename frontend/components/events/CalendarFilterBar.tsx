"use client";
/**
 * @file components/events/CalendarFilterBar.tsx
 * @brief Toolbar above the events calendar: month title + nav, "Today",
 *        calendar filter (popover on desktop, bottom drawer on phone) and
 *        a "New event" action.
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
import type { Calendar } from "@/lib/api/calendars";
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
  onCreate: () => void;
}

/**
 * @brief Events toolbar with month nav and calendar filter.
 * @param props see CalendarFilterBarProps
 * @return toolbar element
 */
export function CalendarFilterBar({
  month,
  onMonthChange,
  selected,
  onSelectedChange,
  calendars,
  onCreate,
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
    <div className="mb-4 flex flex-col gap-3 md:mb-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-muted text-sm">
            Calendar, {format(month, "yyyy")}
          </p>
          <h2 className="text-ink text-4xl leading-none font-black tracking-tight md:text-5xl">
            {format(month, "MMMM")}
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <IconButton
            variant="outline"
            size="sm"
            aria-label="Previous month"
            onClick={() => onMonthChange(subMonths(month, 1))}
          >
            <ChevronLeft className="size-4" />
          </IconButton>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onMonthChange(new Date())}
          >
            Today
          </Button>
          <IconButton
            variant="outline"
            size="sm"
            aria-label="Next month"
            onClick={() => onMonthChange(addMonths(month, 1))}
          >
            <ChevronRight className="size-4" />
          </IconButton>
          <Button onClick={onCreate} className="ml-2">
            New event
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-muted text-sm font-semibold">Calendars</span>
        <div className="hidden md:block">
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
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
              align="start"
              className="max-h-[420px] w-72 overflow-y-auto p-2"
            >
              {picker}
            </PopoverContent>
          </Popover>
        </div>
        <div className="md:hidden">
          <Button
            variant="outline"
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
    </div>
  );
}

export default CalendarFilterBar;
