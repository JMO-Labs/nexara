/**
 * @file components/events/subscriptions/StatusBadge.tsx
 * @brief Sync status indicator for a calendar subscription.
 */
import * as React from "react";
import { AlertCircle, CheckCircle2, Clock } from "lucide-react";

/**
 * @param error last sync error, if any
 * @param lastSynced ISO time of last sync, if any
 * @return icon + text status
 */
export function StatusBadge({
  error,
  lastSynced,
}: {
  error: string | null;
  lastSynced: string | null;
}) {
  const [Icon, label, cls] = error
    ? [AlertCircle, "Error", "text-destructive"]
    : !lastSynced
      ? [Clock, "Pending", "text-muted"]
      : [CheckCircle2, "Synced", "text-leaf"];
  return (
    <span className={`flex items-center gap-1 text-sm ${cls}`}>
      <Icon aria-hidden className="size-4 shrink-0" />
      {label}
    </span>
  );
}
