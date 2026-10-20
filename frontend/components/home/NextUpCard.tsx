"use client";
/**
 * @file components/home/NextUpCard.tsx
 * @brief Featured card for the viewer's next event.
 */
import * as React from "react";
import Link from "next/link";
import { format, parseISO } from "date-fns";
import { Card } from "@/components/ui";
import { useUpcomingEvents } from "@/hooks/useEvents";
import type { EventItem } from "@/lib/api/events";

const GOING = new Set(["attending", "yes", "maybe"]);

/**
 * @brief Pick the nearest RSVP'd event, else the nearest event.
 * @param events upcoming events
 * @return chosen event or undefined
 */
function pick(events: EventItem[]): EventItem | undefined {
  const sorted = [...events].sort((a, b) =>
    a.starts_at.localeCompare(b.starts_at),
  );
  return (
    sorted.find((e) => e.user_rsvp && GOING.has(e.user_rsvp.status)) ??
    sorted[0]
  );
}

/**
 * @brief Next-up event card; renders nothing without events.
 * @return card link or null
 */
export function NextUpCard() {
  const { data } = useUpcomingEvents(30);
  const e = pick(data?.items ?? []);
  if (!e) return null;
  const d = parseISO(e.starts_at);
  const going = e.rsvp_counts.attending ?? e.rsvp_counts.yes ?? 0;
  return (
    <Card tone="featured" className="p-4 mb-4">
      <Link href="/app/events" className="flex items-center gap-4">
        <div
          aria-hidden="true"
          className="bg-accent text-surface-strong rounded-2xl px-3 py-2 text-center"
        >
          <div className="font-black text-2xl leading-none">
            {format(d, "d")}
          </div>
          <div className="text-xs uppercase">{format(d, "EEE")}</div>
        </div>
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide">Next up</p>
          <p className="font-bold truncate">{e.title}</p>
          <p className="text-sm truncate">
            {e.location ? `${e.location} · ` : ""}
            {going} going
          </p>
        </div>
      </Link>
    </Card>
  );
}

export default NextUpCard;
