"use client";
/**
 * @file components/events/event-detail/ExportIcalButton.tsx
 * @brief Button downloading a single event as an .ics file (authed fetch).
 */
import * as React from "react";
import { CalendarPlus } from "lucide-react";
import { useTranslations } from "next-intl";
import { exportEventIcal } from "@/lib/api/events";

/** Strip characters invalid in common filesystems; fall back to "event". */
function icsFilename(title: string): string {
  const safe = title.replace(/[\\/:*?"<>|]+/g, "").trim();
  return `${safe || "event"}.ics`;
}

/** Save a Blob via a temporary object URL and anchor click. */
function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/**
 * @param eventId event to export
 * @param title event title, used as the download filename
 * @return text-styled button that downloads the event's .ics
 */
export function ExportIcalButton({
  eventId,
  title,
}: {
  eventId: string;
  title: string;
}) {
  const t = useTranslations("events");
  const [busy, setBusy] = React.useState(false);
  const [failed, setFailed] = React.useState(false);

  const onClick = async () => {
    setBusy(true);
    setFailed(false);
    try {
      saveBlob(await exportEventIcal(eventId), icsFilename(title));
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={onClick}
        disabled={busy}
        aria-busy={busy}
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-accent underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-60"
      >
        <CalendarPlus className="size-4" aria-hidden="true" />
        {t("exportIcal")}
      </button>
      {failed && (
        <p role="alert" className="mt-1 text-xs text-danger">
          {t("exportIcalFailed")}
        </p>
      )}
    </>
  );
}
