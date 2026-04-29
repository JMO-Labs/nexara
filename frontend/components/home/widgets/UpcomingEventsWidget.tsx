"use client";
/**
 * @file components/home/widgets/UpcomingEventsWidget.tsx
 * @brief Upcoming events widget with time-window select and subgroup filters.
 *        Clicking an event row opens EventDetailPanel in place.
 */
import * as React from "react";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import { useUpcomingEvents } from "@/hooks/useEvents";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { EmptyState, Skeleton } from "@/components/ui";
import { EventDetailPanel } from "@/components/events/EventDetailPanel";
import { SourceBadge } from "@/components/feed/SourceBadge";
import type { EventItem } from "@/lib/api/events";
import type { Subgroup } from "@/lib/api/subgroups";
import type { WidgetContext } from "@/lib/widgets/registry";
import { format, parseISO, isToday, isTomorrow } from "date-fns";

function formatEventTime(starts: string, allDay: boolean): string {
  const d = parseISO(starts);
  if (allDay) {
    if (isToday(d)) return "Today · All day";
    if (isTomorrow(d)) return "Tomorrow · All day";
    return format(d, "EEE, MMM d") + " · All day";
  }
  if (isToday(d)) return "Today " + format(d, "h:mm a");
  if (isTomorrow(d)) return "Tomorrow " + format(d, "h:mm a");
  return format(d, "EEE, MMM d") + " " + format(d, "h:mm a");
}

const DAYS_OPTIONS = [7, 14, 30] as const;

export function UpcomingEventsWidget(_: WidgetContext) {
  const [days, setDays] = React.useState<7 | 14 | 30>(14);
  const [filterSubgroupId, setFilterSubgroupId] = React.useState<string | undefined>(undefined);
  const [selectedEvent, setSelectedEvent] = React.useState<EventItem | null>(null);
  const containerRef = React.useRef<HTMLDivElement | null>(null);

  const { data, isLoading } = useUpcomingEvents(days, filterSubgroupId);
  const { data: subgroupsData } = useSubgroupList();

  const events = data?.items ?? [];

  const subgroupNameMap = React.useMemo(() => {
    const m = new Map<string, string>();
    (subgroupsData as Subgroup[] | undefined ?? []).forEach((sg) => m.set(sg.id, sg.name));
    return m;
  }, [subgroupsData]);

  const subgroups = subgroupsData ?? [];

  return (
    <div ref={containerRef} className="relative">
      <Stack spacing={1.5}>
        {/* Controls row */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex gap-1">
            {DAYS_OPTIONS.map((d) => (
              <button
                key={d}
                type="button"
                aria-pressed={days === d}
                onClick={() => setDays(d)}
                className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)] ${
                  days === d
                    ? "bg-indigo-600 text-white"
                    : "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700"
                }`}
              >
                {d}d
              </button>
            ))}
          </div>
          {subgroups.length > 0 && (
            <div className="flex flex-wrap gap-1">
              <button
                type="button"
                aria-pressed={filterSubgroupId === undefined}
                onClick={() => setFilterSubgroupId(undefined)}
                className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)] ${
                  filterSubgroupId === undefined
                    ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
                    : "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400 hover:bg-neutral-200"
                }`}
              >
                All
              </button>
              {(subgroups as Subgroup[]).slice(0, 5).map((sg) => (
                <button
                  key={sg.id}
                  type="button"
                  aria-pressed={filterSubgroupId === sg.id}
                  onClick={() => setFilterSubgroupId(sg.id)}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)] ${
                    filterSubgroupId === sg.id
                      ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
                      : "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400 hover:bg-neutral-200"
                  }`}
                >
                  {sg.name}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Events list */}
        {isLoading ? (
          <Stack spacing={1}>
            {[0, 1, 2].map((i) => <Skeleton key={i} height={52} rounded="md" />)}
          </Stack>
        ) : events.length === 0 ? (
          <EmptyState title="No upcoming events" description={`Nothing scheduled in the next ${days} days.`} />
        ) : (
          <Stack spacing={0.5}>
            {events.slice(0, 10).map((event) => (
              <button
                key={event.id}
                type="button"
                onClick={() => setSelectedEvent(event)}
                className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)]"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <Typography level="body-sm" fontWeight="md" noWrap>
                      {event.title}
                    </Typography>
                    <Typography level="body-xs" textColor="text.tertiary">
                      {formatEventTime(event.starts_at, event.is_all_day)}
                    </Typography>
                  </div>
                  <SourceBadge
                    subgroupId={event.subgroup_id}
                    subgroupName={event.subgroup_id ? (subgroupNameMap.get(event.subgroup_id) ?? null) : null}
                  />
                </div>
              </button>
            ))}
          </Stack>
        )}
      </Stack>

      {/* EventDetailPanel */}
      <EventDetailPanel
        containerRef={containerRef}
        event={selectedEvent}
        subgroupNames={subgroupNameMap}
        onClose={() => setSelectedEvent(null)}
      />
    </div>
  );
}

export default UpcomingEventsWidget;
