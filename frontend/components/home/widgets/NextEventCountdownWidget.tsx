"use client";
/**
 * @file components/home/widgets/NextEventCountdownWidget.tsx
 * @brief Countdown to the user's next upcoming event, linking to the event.
 */
import Link from "next/link";
import { useUpcomingEvents } from "@/hooks/useEvents";
import { EmptyState, Skeleton } from "@/components/ui";
import { EventCountdown } from "@/components/events/EventCountdown";

/**
 * @brief Next-event countdown widget body.
 * @return countdown link, skeleton or empty state
 */
export function NextEventCountdownWidget() {
  const { data, isLoading } = useUpcomingEvents(30);
  const next = data?.items?.find(
    (e) => new Date(e.starts_at).getTime() > Date.now(),
  );

  if (isLoading) return <Skeleton height={96} rounded="md" />;
  if (!next) {
    return (
      <EmptyState
        compact
        title="No upcoming events"
        description="Nothing scheduled in the next 30 days."
      />
    );
  }
  return (
    <Link
      href={`/app/events?event=${encodeURIComponent(next.id)}`}
      aria-label={`Next event: ${next.title}`}
      className="block rounded-xl hover:bg-bg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      <EventCountdown event={next} key={next.id} />
    </Link>
  );
}

export default NextEventCountdownWidget;
