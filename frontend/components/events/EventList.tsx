"use client";
/**
 * @file components/events/EventList.tsx
 * @brief Vertical list of EventCards grouped by month with sticky headers.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { listStagger, listItem } from "@/components/ui/motion";
import { Skeleton, EmptyState, Button } from "@/components/ui";
import { EventCard } from "./EventCard";
import { useUpcomingEvents } from "@/hooks/useEvents";
import type { EventItem } from "@/lib/api/events";

function monthKey(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

/**
 * @brief Upcoming events grouped by month.
 * @return list, skeleton or empty/error state
 */
export function EventList() {
  const router = useRouter();
  const { data, isLoading, error } = useUpcomingEvents(60);
  const reduced = useReducedMotion();
  const stagger = reduced
    ? {}
    : { variants: listStagger, initial: "hidden", animate: "show" };
  const item = reduced ? {} : { variants: listItem };

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} height={140} rounded="lg" />
        ))}
      </div>
    );
  }
  if (error)
    return (
      <EmptyState
        title="Couldn't load events"
        description={String(error)}
        action={
          <Button variant="ghost" onClick={() => router.refresh()}>
            Retry
          </Button>
        }
      />
    );
  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title="No upcoming events"
        description="Once events are scheduled they'll appear here."
        action={
          <Button onClick={() => router.push("/app/events")}>
            View all events
          </Button>
        }
      />
    );
  }

  const groups: Record<string, EventItem[]> = {};
  for (const ev of data.items) {
    const k = monthKey(ev.starts_at);
    (groups[k] ??= []).push(ev);
  }

  return (
    <div className="flex flex-col">
      {Object.entries(groups).map(([month, items]) => (
        <React.Fragment key={month}>
          <h3 className="sticky top-0 z-10 border-b border-current/15 bg-bg px-4 py-2 text-sm font-semibold text-muted">
            {month}
          </h3>
          <motion.div className="flex flex-col gap-3 p-4" {...stagger}>
            {items.map((ev) => (
              <motion.div key={ev.id} {...item}>
                <EventCard event={ev} />
              </motion.div>
            ))}
          </motion.div>
        </React.Fragment>
      ))}
    </div>
  );
}

export default EventList;
