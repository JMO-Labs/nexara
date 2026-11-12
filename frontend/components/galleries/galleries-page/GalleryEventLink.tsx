/**
 * @file components/galleries/galleries-page/GalleryEventLink.tsx
 * @brief "Linked to event" line shown in a gallery header.
 */
import Link from "next/link";
import { CalendarDays } from "lucide-react";

/**
 * @brief Link back to the event a gallery belongs to.
 * @param eventId linked event id, or null/undefined
 * @param title optional event title (falls back to "View event")
 * @return link element or null
 */
export function GalleryEventLink({
  eventId,
  title,
}: {
  eventId?: string | null;
  title?: string;
}) {
  if (!eventId) return null;
  return (
    <p className="text-muted flex items-center gap-2 text-sm">
      <CalendarDays className="size-4" aria-hidden="true" />
      <span>Linked to event:</span>
      <Link
        href={`/app/events?event=${encodeURIComponent(eventId)}`}
        className="text-accent font-semibold underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        {title ?? "View event"}
      </Link>
    </p>
  );
}
