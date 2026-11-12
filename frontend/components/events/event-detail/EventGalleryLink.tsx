/**
 * @file components/events/event-detail/EventGalleryLink.tsx
 * @brief "View gallery" link shown on an event that has a linked gallery.
 */
import Link from "next/link";
import { Images } from "lucide-react";

/**
 * @brief Link to the event's gallery.
 * @param galleryId linked gallery id, or null/undefined when none
 * @return link element or null
 */
export function EventGalleryLink({ galleryId }: { galleryId?: string | null }) {
  if (!galleryId) return null;
  return (
    <Link
      href={`/app/galleries?gallery=${encodeURIComponent(galleryId)}`}
      className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-lg border border-ink/15 px-3 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      <Images className="size-4" aria-hidden="true" />
      View gallery
    </Link>
  );
}
