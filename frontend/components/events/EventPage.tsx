"use client";
/**
 * @file components/events/EventPage.tsx
 * @brief Standalone full-page event view (shareable): PageHeader with back
 *        link and a glass Panel reusing EventDetailBody.
 */
import { Skeleton } from "@/components/ui";
import { PageHeader } from "@/components/ui/page/PageHeader";
import { Panel } from "@/components/ui/page/Panel";
import { useEventDetail } from "@/hooks/useEvents";
import { ApiError } from "@/lib/api/errors";
import { EventCountdown } from "./EventCountdown";
import { EventDetailBody } from "./event-detail/EventDetailBody";

const BACK = { href: "/app/events", label: "Back to events" };

/**
 * @brief Full-page event view.
 * @param id event id
 * @return page content (skeleton, not-found, or event)
 */
export function EventPage({ id }: { id: string }) {
  const { data: event, isLoading, error } = useEventDetail(id);
  const notFound = error instanceof ApiError && error.status === 404;

  return (
    <div className="mx-auto w-full max-w-3xl">
      <PageHeader title={event?.title ?? "Event"} back={BACK} />
      {isLoading ? (
        <Panel as="div" className="flex flex-col gap-3">
          <Skeleton height={32} width="60%" />
          <Skeleton height={20} width="40%" />
          <Skeleton height={160} />
        </Panel>
      ) : notFound ? (
        <Panel as="div">
          <p role="alert" className="text-lg font-semibold">
            Event not found
          </p>
        </Panel>
      ) : error || !event ? (
        <Panel as="div">
          <p role="alert" className="text-lg font-semibold">
            Could not load event
          </p>
        </Panel>
      ) : (
        <Panel as="div">
          {new Date(event.starts_at).getTime() > Date.now() && (
            <EventCountdown event={event} />
          )}
          <EventDetailBody event={event} />
        </Panel>
      )}
    </div>
  );
}
