"use client";
/**
 * @file components/events/event-detail/EventDetailBody.tsx
 * @brief Scrollable body of the event detail panel: when, where, map,
 *        description, RSVP and contribution slots.
 */
import dynamic from "next/dynamic";
import { CalendarDays, MapPin, ExternalLink } from "lucide-react";
import { Markdown } from "@/components/ui";
import { RsvpInline } from "../RsvpInline";
import type { EventItem } from "@/lib/api/events";
import { mapsUrlForCoords } from "@/lib/geo/openInMaps";
import { EventGalleryLink } from "./EventGalleryLink";
import { ContributionSlots } from "./ContributionSlots";
import { formatRange } from "./formatRange";
import { ExportIcalButton } from "./ExportIcalButton";

const EventMiniMap = dynamic(
  () => import("../EventMiniMap").then((m) => m.EventMiniMap),
  { ssr: false, loading: () => null },
);

/**
 * @brief Body content for an event.
 * @param event the event to show
 * @return scroll container
 */
export function EventDetailBody({ event }: { event: EventItem }) {
  const hasCoords = event.latitude != null && event.longitude != null;
  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4 md:px-6">
      <div className="mb-3 flex flex-col gap-2 text-sm md:flex-row md:gap-8">
        <div className="flex items-center gap-2">
          <CalendarDays className="size-4" aria-hidden="true" />
          <span>
            {formatRange(event.starts_at, event.ends_at, event.is_all_day)}
          </span>
        </div>
        {event.location && (
          <div className="flex flex-wrap items-center gap-2">
            <MapPin className="size-4" aria-hidden="true" />
            <span>{event.location}</span>
            {hasCoords && (
              <a
                href={mapsUrlForCoords(event.latitude!, event.longitude!)}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-1 inline-flex items-center gap-1 text-xs font-semibold text-accent underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Open in Google Maps
                <ExternalLink className="size-3" aria-hidden="true" />
              </a>
            )}
          </div>
        )}
      </div>
      {hasCoords && (
        <div className="mb-4 max-w-[480px]">
          <EventMiniMap
            lat={event.latitude!}
            lon={event.longitude!}
            height={180}
          />
        </div>
      )}
      {event.description && (
        <div className="mb-4 max-w-[72ch] text-sm text-muted">
          <Markdown content={event.description} size="sm" />
        </div>
      )}
      <div className="mb-4">
        <ExportIcalButton eventId={event.id} title={event.title} />
      </div>
      <RsvpInline
        eventId={event.id}
        labels={event.rsvp_labels}
        current={event.user_rsvp?.status ?? null}
        counts={event.rsvp_counts}
      />
      <EventGalleryLink galleryId={event.gallery_id} />
      <ContributionSlots eventId={event.id} slots={event.contribution_slots} />
    </div>
  );
}
