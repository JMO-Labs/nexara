"use client";
/**
 * @file components/events/EventCard.tsx
 * @brief Event tile: title, schedule, location, RSVP row.
 */
import * as React from "react";
import { MapPin } from "lucide-react";
import { Card, Markdown } from "@/components/ui";
import { RsvpInline } from "./RsvpInline";
import type { EventItem } from "@/lib/api/events";

export interface EventCardProps {
  event: EventItem;
}

function formatRange(starts: string, ends: string, allDay: boolean): string {
  const s = new Date(starts);
  const e = new Date(ends);
  const date = s.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  if (allDay) return `${date} · All day`;
  const t = (d: Date) =>
    d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  return `${date} · ${t(s)} – ${t(e)}`;
}

/**
 * @brief Event tile.
 * @param event event to render
 * @return card element
 */
export function EventCard({ event }: EventCardProps) {
  return (
    <Card className="flex flex-col gap-2 p-4">
      <h3 className="text-lg font-semibold">{event.title}</h3>
      <p className="text-sm text-muted">
        {formatRange(event.starts_at, event.ends_at, event.is_all_day)}
      </p>
      {event.location && (
        <p className="flex items-center gap-1.5 text-sm">
          <MapPin aria-hidden className="size-4 shrink-0" />
          {event.location}
        </p>
      )}
      {event.description && (
        <div className="text-sm">
          <Markdown
            content={event.description}
            size="sm"
            truncate
            clampLines={4}
          />
        </div>
      )}
      <RsvpInline
        eventId={event.id}
        labels={event.rsvp_labels}
        current={event.user_rsvp?.status ?? null}
        counts={event.rsvp_counts}
      />
    </Card>
  );
}

export default EventCard;
