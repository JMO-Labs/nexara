"use client";
/**
 * @file components/events/EventPage.tsx
 * @brief Standalone full-page event view (shareable) reusing EventDetailBody.
 */
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Skeleton } from "@/components/ui";
import { useEventDetail } from "@/hooks/useEvents";
import { ApiError } from "@/lib/api/errors";
import { EventCountdown } from "./EventCountdown";
import { EventDetailBody } from "./event-detail/EventDetailBody";

function BackLink() {
  return (
    <Link
      href="/app/events"
      className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      <ArrowLeft className="size-4" aria-hidden="true" />
      Back to events
    </Link>
  );
}

/**
 * @brief Full-page event view.
 * @param id event id
 * @return page content (skeleton, not-found, or event)
 */
export function EventPage({ id }: { id: string }) {
  const { data: event, isLoading, error } = useEventDetail(id);
  const notFound = error instanceof ApiError && error.status === 404;

  return (
    <div className="mx-auto w-full max-w-3xl p-4 md:p-6">
      <BackLink />
      {isLoading ? (
        <div className="flex flex-col gap-3">
          <Skeleton height={32} width="60%" />
          <Skeleton height={20} width="40%" />
          <Skeleton height={160} />
        </div>
      ) : notFound ? (
        <p role="alert" className="text-lg font-semibold">
          Event not found
        </p>
      ) : error || !event ? (
        <p role="alert" className="text-lg font-semibold">
          Could not load event
        </p>
      ) : (
        <>
          <h1 className="mb-3 text-2xl font-bold">{event.title}</h1>
          {new Date(event.starts_at).getTime() > Date.now() && (
            <EventCountdown event={event} />
          )}
          <EventDetailBody event={event} />
        </>
      )}
    </div>
  );
}
