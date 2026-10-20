/**
 * @file components/events/calendar-filter-bar/groups.ts
 * @brief Pure helpers that group calendars by kind for the filter UI.
 */
import { toneForSubgroupId } from "../eventColors";
import type { Calendar } from "@/lib/api/calendars";

export type CalendarSourceId = string;

export interface CalendarOption {
  id: CalendarSourceId;
  label: string;
  color: string;
}

export interface CalendarGroup {
  kind: "community" | "personal" | "subgroup";
  label: string;
  options: CalendarOption[];
}

const GROUP_LABELS: Record<CalendarGroup["kind"], string> = {
  community: "Community",
  personal: "Personal",
  subgroup: "Groups",
};

const GROUP_ORDER: CalendarGroup["kind"][] = [
  "community",
  "personal",
  "subgroup",
];

function colorFor(cal: Calendar): string {
  if (cal.color) return cal.color;
  if (cal.kind === "subgroup" && cal.subgroup_id) {
    return toneForSubgroupId(cal.subgroup_id).solid;
  }
  if (cal.kind === "community") return toneForSubgroupId(null).solid;
  return "#b45309";
}

/**
 * @brief Bucket calendars by kind, sorted by name, empty groups dropped.
 * @param calendars all calendars
 * @return ordered groups
 */
export function buildGroups(calendars: Calendar[]): CalendarGroup[] {
  const buckets: Record<CalendarGroup["kind"], CalendarOption[]> = {
    community: [],
    personal: [],
    subgroup: [],
  };
  for (const cal of calendars) {
    buckets[cal.kind].push({
      id: cal.id,
      label: cal.name,
      color: colorFor(cal),
    });
  }
  for (const k of GROUP_ORDER) {
    buckets[k].sort((a, b) => a.label.localeCompare(b.label));
  }
  return GROUP_ORDER.filter((k) => buckets[k].length > 0).map((k) => ({
    kind: k,
    label: GROUP_LABELS[k],
    options: buckets[k],
  }));
}

/**
 * @brief Short summary label for the filter trigger.
 * @param selectedCount selected calendars
 * @param total all calendars
 * @return label text
 */
export function summarize(selectedCount: number, total: number): string {
  if (selectedCount === 0) return "No calendars";
  if (selectedCount === total) return "All calendars";
  if (selectedCount === 1) return "1 calendar";
  return `${selectedCount} calendars`;
}
