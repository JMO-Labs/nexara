/**
 * @file components/galleries/EventGalleryBadge.tsx
 * @brief Badge marking a gallery linked to an event.
 */
import * as React from "react";
import { CalendarDays } from "lucide-react";
import { Badge } from "@/components/ui";

/**
 * @brief "Event gallery" badge with decorative calendar icon.
 * @return badge element
 */
export function EventGalleryBadge() {
  return (
    <Badge tone="accent">
      <CalendarDays className="size-3" aria-hidden="true" />
      Event gallery
    </Badge>
  );
}

export default EventGalleryBadge;
