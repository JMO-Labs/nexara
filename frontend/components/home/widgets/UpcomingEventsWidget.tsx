"use client";
/**
 * @file components/home/widgets/UpcomingEventsWidget.tsx
 * @brief Compact list of the next events (14 days); click opens the detail panel.
 */
import * as React from "react";
import { format, parseISO } from "date-fns";
import { useUpcomingEvents } from "@/hooks/useEvents";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { EmptyState, Skeleton } from "@/components/ui";
import { EventDetailPanel } from "@/components/events/EventDetailPanel";
import type { EventItem } from "@/lib/api/events";
import type { Subgroup } from "@/lib/api/subgroups";

/**
 * @brief Upcoming events widget body.
 * @return list, skeleton or empty state
 */
export function UpcomingEventsWidget() {
  const [selected, setSelected] = React.useState<EventItem | null>(null);
  const { data, isLoading } = useUpcomingEvents(14);
  const { data: subgroups } = useSubgroupList();
  const names = React.useMemo(
    () =>
      new Map(
        ((subgroups as Subgroup[] | undefined) ?? []).map((s) => [
          s.id,
          s.name,
        ]),
      ),
    [subgroups],
  );
  const events = (data?.items ?? []).slice(0, 5);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} height={40} rounded="md" />
        ))}
      </div>
    );
  }
  if (events.length === 0) {
    return (
      <EmptyState
        compact
        title="No upcoming events"
        description="Nothing scheduled in the next 14 days."
      />
    );
  }
  return (
    <>
      <ul className="flex flex-col gap-1">
        {events.map((e) => (
          <li key={e.id}>
            <button
              type="button"
              onClick={() => setSelected(e)}
              className="w-full text-left rounded-xl px-2 py-1.5 hover:bg-bg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <span className="block text-sm font-semibold text-ink truncate">
                {e.title}
              </span>
              <span className="block text-xs text-muted">
                {format(parseISO(e.starts_at), "EEE, MMM d")}
                {e.is_all_day
                  ? ""
                  : `, ${format(parseISO(e.starts_at), "h:mm a")}`}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <EventDetailPanel
        event={selected}
        subgroupNames={names}
        onClose={() => setSelected(null)}
      />
    </>
  );
}

export default UpcomingEventsWidget;
