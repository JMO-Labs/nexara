"use client";
/**
 * @file components/events/calendar-filter-bar/CalendarPicker.tsx
 * @brief Grouped multi-select checklist of calendars (all / group / item).
 */
import * as React from "react";
import { Checkbox } from "@/components/ui";
import type { CalendarGroup, CalendarSourceId } from "./groups";

export interface CalendarPickerProps {
  groups: CalendarGroup[];
  selected: CalendarSourceId[];
  onSelectedChange: (ids: CalendarSourceId[]) => void;
}

function Swatch({ color }: { color: string }) {
  return (
    <span
      aria-hidden
      className="size-2.5 shrink-0 rounded-full"
      style={{ backgroundColor: color }}
    />
  );
}

const ROW =
  "flex min-h-11 cursor-pointer items-center gap-3 rounded-xl px-2 hover:bg-bg";

/**
 * @brief Checklist of calendars grouped by kind.
 * @param props groups, selected ids, change handler
 * @return picker element
 */
export function CalendarPicker({
  groups,
  selected,
  onSelectedChange,
}: CalendarPickerProps) {
  const selectedSet = React.useMemo(() => new Set(selected), [selected]);
  const allIds = groups.flatMap((g) => g.options.map((o) => o.id));
  const allOn = allIds.length > 0 && selected.length === allIds.length;

  const toggleOne = (id: CalendarSourceId) =>
    onSelectedChange(
      selectedSet.has(id)
        ? selected.filter((x) => x !== id)
        : [...selected, id],
    );

  const toggleAll = () => onSelectedChange(allOn ? [] : allIds);

  const groupState = (g: CalendarGroup): boolean | "indeterminate" => {
    const on = g.options.filter((o) => selectedSet.has(o.id)).length;
    if (on === 0) return false;
    return on === g.options.length ? true : "indeterminate";
  };

  const toggleGroup = (g: CalendarGroup) => {
    const ids = g.options.map((o) => o.id);
    if (groupState(g) === true) {
      onSelectedChange(selected.filter((x) => !ids.includes(x)));
    } else {
      onSelectedChange([...new Set([...selected, ...ids])]);
    }
  };

  return (
    <div className="flex flex-col gap-1">
      <label className={ROW}>
        <Checkbox
          checked={allOn ? true : selected.length > 0 ? "indeterminate" : false}
          onCheckedChange={toggleAll}
        />
        <span className="text-sm font-semibold">All calendars</span>
      </label>
      {groups.map((g) => (
        <div key={g.kind} className="border-t border-ink/10 pt-1">
          <label className={ROW}>
            <Checkbox
              checked={groupState(g)}
              onCheckedChange={() => toggleGroup(g)}
            />
            <span className="text-muted flex-1 text-sm font-semibold">
              {g.label}
            </span>
            <span className="text-muted text-xs">
              {g.options.filter((o) => selectedSet.has(o.id)).length}/
              {g.options.length}
            </span>
          </label>
          {g.options.map((o) => (
            <label key={o.id} className={`${ROW} pl-8`}>
              <Checkbox
                checked={selectedSet.has(o.id)}
                onCheckedChange={() => toggleOne(o.id)}
              />
              <Swatch color={o.color} />
              <span className="flex-1 text-sm">{o.label}</span>
            </label>
          ))}
        </div>
      ))}
    </div>
  );
}

export { Swatch };
