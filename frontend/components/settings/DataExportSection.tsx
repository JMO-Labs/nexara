"use client";
/**
 * @file components/settings/DataExportSection.tsx
 * @brief "Download My Data" section: request, progress, download, expiry.
 */
import { useEffect, useState } from "react";
import { Button, Card } from "@/components/ui";
import {
  useExportHistory,
  useExportStatus,
  useRequestExport,
} from "@/hooks/useDataExport";
import { ApiError } from "@/lib/api/errors";
import type { DataExport } from "@/lib/api/dataExport";

const LABEL = "Download My Data";

/** @brief Whole hours until iso (min 0), re-evaluated every minute. */
function useHoursLeft(iso: string | null | undefined): number | null {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(t);
  }, []);
  if (!iso) return null;
  return Math.max(0, Math.ceil((new Date(iso).getTime() - now) / 3600_000));
}

/** @brief Map a request error to user text. */
function requestError(e: unknown): string {
  return e instanceof ApiError && e.status === 429
    ? "You can request one export per day. Try again tomorrow."
    : "Failed to request export. Please try again.";
}

/** @brief Past exports list. */
function History({ items }: { items: DataExport[] }) {
  if (!items.length) return null;
  return (
    <section aria-label="Previous exports" className="mt-4">
      <h3 className="text-sm font-bold">Previous exports</h3>
      <ul className="mt-1 text-sm text-muted">
        {items.map((x) => (
          <li key={x.id}>
            {new Date(x.created_at).toLocaleDateString()} - {x.status}
            {x.downloaded_at &&
              ` - Downloaded on ${new Date(x.downloaded_at).toLocaleDateString()}`}
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * @brief Data export settings section.
 * @return section content
 */
export function DataExportSection() {
  const history = useExportHistory();
  const request = useRequestExport();
  const [id, setId] = useState<string | null>(null);
  const activeId = id ?? history.data?.[0]?.id ?? null;
  const { data: exp } = useExportStatus(activeId);
  const hours = useHoursLeft(exp?.status === "ready" ? exp.expires_at : null);

  const status = exp?.status;
  const busy =
    request.isPending || status === "pending" || status === "processing";
  const start = () =>
    request.mutate(undefined, { onSuccess: (r) => setId(r.export_id) });

  let message: string | null = null;
  if (request.isError) message = requestError(request.error);
  else if (busy && !request.isPending)
    message =
      "Generating your data... This may take a few minutes. You'll be notified when ready.";
  else if (status === "expired")
    message = "Your export link expired. Request a new one.";
  else if (status === "failed")
    message = "Your export failed. Please try again.";

  return (
    <Card className="p-4">
      <h2 className="text-lg font-bold">{LABEL}</h2>
      <p className="mt-1 text-sm text-muted">
        Request a ZIP file with all your posts, comments, media, events, and
        profile data. Downloads expire after 48 hours.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        {status === "ready" && exp ? (
          <Button asChild>
            <a href={`/api/v1/export/${encodeURIComponent(exp.id)}/download`}>
              Download
            </a>
          </Button>
        ) : (
          <Button onClick={start} disabled={busy}>
            {status === "failed" ? "Retry" : LABEL}
          </Button>
        )}
        {hours !== null && (
          <span className="text-sm">Expires in {hours} hours</span>
        )}
      </div>
      <p role="status" aria-live="polite" className="mt-2 text-sm">
        {message}
      </p>
      <History items={history.data ?? []} />
    </Card>
  );
}
