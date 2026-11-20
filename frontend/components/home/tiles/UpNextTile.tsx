"use client";
/**
 * @file components/home/tiles/UpNextTile.tsx
 * @brief Up next tile: next three upcoming events with inline RSVP.
 */
import Link from "next/link";
import { Calendar, Check } from "lucide-react";
import { HomeTile, type TileSlotProps } from "@/components/home/HomeTile";
import { useUpcomingEvents, useRsvp } from "@/hooks/useEvents";
import type { EventItem } from "@/lib/api/events";
import { inScope, useHomeScope } from "@/stores/homeScope";

const WEEKDAY = new Intl.DateTimeFormat(undefined, { weekday: "short" });
const TIME = new Intl.DateTimeFormat(undefined, {
  hour: "numeric",
  minute: "2-digit",
});

/** @brief One event row with date block and RSVP state. */
function EventRow({ event }: { event: EventItem }) {
  const rsvp = useRsvp(event.id);
  const d = new Date(event.starts_at);
  const going = event.user_rsvp?.status === "attending";
  const when = event.is_all_day ? "All day" : TIME.format(d);
  return (
    <li className="flex items-center gap-3 py-2">
      <div className="flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-xl bg-white/40">
        <span className="text-xs text-[var(--nx-muted)]">
          {WEEKDAY.format(d)}
        </span>
        <span className="text-lg font-medium leading-none">{d.getDate()}</span>
      </div>
      <Link href={`/app/events/${event.id}`} className="min-w-0 flex-1">
        <span className="block truncate font-medium">{event.title}</span>
        <span className="block truncate text-sm text-[var(--nx-muted)]">
          {event.location ? `${when}, ${event.location}` : when}
        </span>
      </Link>
      {going ? (
        <Check
          aria-label="Going"
          role="img"
          className="h-5 w-5 text-[var(--nx-ok)]"
        />
      ) : (
        <button
          type="button"
          onClick={() => rsvp.mutate("attending")}
          aria-label={`RSVP to ${event.title}`}
          className="sweep rounded-full px-3 py-1 text-sm font-medium"
        >
          RSVP
        </button>
      )}
    </li>
  );
}

/**
 * @brief Up next tile.
 * @param props open/onToggle from the home page
 * @return HomeTile
 */
export function UpNextTile({ open, onToggle }: TileSlotProps) {
  const scope = useHomeScope((s) => s.scope);
  const { data } = useUpcomingEvents(30);
  const events = (data?.items ?? [])
    .filter((e) => inScope(e.subgroup_id, scope))
    .slice(0, 3);
  const pending = events.filter((e) => e.user_rsvp?.status !== "attending");
  const first = events[0];
  const summary = first
    ? `${first.title}, ${WEEKDAY.format(new Date(first.starts_at))}`
    : "No upcoming events";
  return (
    <HomeTile
      id="next"
      title="Up next"
      icon={Calendar}
      href="/app/events"
      linkLabel="See calendar"
      summary={summary}
      count={pending.length}
      hot={pending.length > 0}
      open={open}
      onToggle={onToggle}
      className="md:[grid-area:next]"
    >
      {events.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-6 text-center">
          <p className="text-sm text-[var(--nx-muted)]">Nothing coming up</p>
          <Link href="/app/events" className="text-sm underline">
            Plan an event
          </Link>
        </div>
      ) : (
        <ul>
          {events.map((e) => (
            <EventRow key={e.id} event={e} />
          ))}
        </ul>
      )}
    </HomeTile>
  );
}
