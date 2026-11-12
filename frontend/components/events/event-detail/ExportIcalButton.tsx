"use client";
/**
 * @file components/events/event-detail/ExportIcalButton.tsx
 * @brief Download link exporting a single event as an .ics file.
 */
import { CalendarPlus } from "lucide-react";
import { useTranslations } from "next-intl";

/**
 * @param eventId event to export
 * @return anchor styled as a text button
 */
export function ExportIcalButton({ eventId }: { eventId: string }) {
  const t = useTranslations("events");
  return (
    <a
      href={`/api/v1/events/${encodeURIComponent(eventId)}/ical`}
      download
      className="inline-flex items-center gap-1.5 text-xs font-semibold text-accent underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      <CalendarPlus className="size-4" aria-hidden="true" />
      {t("exportIcal")}
    </a>
  );
}
