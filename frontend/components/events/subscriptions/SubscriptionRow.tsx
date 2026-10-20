"use client";
/**
 * @file components/events/subscriptions/SubscriptionRow.tsx
 * @brief Single calendar subscription row with sync interval, sync, delete.
 */
import * as React from "react";
import { RefreshCw, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { formatDistanceToNow } from "date-fns";
import { Button, IconButton, Modal, Select, Option } from "@/components/ui";
import type { CalendarSubscription } from "@/lib/api/events";
import { StatusBadge } from "./StatusBadge";
import { INTERVALS } from "./intervals";

export interface SubscriptionRowProps {
  sub: CalendarSubscription;
  onDelete: (id: string) => void;
  onSync: (id: string) => void;
  isSyncing: boolean;
}

/**
 * @param props subscription and handlers
 * @return row (stacked on phone, grid from md)
 */
export function SubscriptionRow({
  sub,
  onDelete,
  onSync,
  isSyncing,
}: SubscriptionRowProps) {
  const t = useTranslations();
  const [showDelete, setShowDelete] = React.useState(false);
  const [interval, setInterval] = React.useState(sub.sync_interval_minutes);

  return (
    <>
      <div className="grid grid-cols-[1fr_auto] items-center gap-x-2 gap-y-1 border-b border-current/15 px-4 py-3 last:border-b-0 hover:bg-bg md:grid-cols-[1fr_1.2fr_1fr_0.8fr_0.9fr_auto_auto]">
        <span className="truncate text-sm font-semibold">{sub.title}</span>
        <span className="order-last col-span-2 truncate font-mono text-xs text-muted md:order-none md:col-span-1">
          {sub.source_url}
        </span>
        <span className="text-xs text-muted">
          {sub.last_synced_at
            ? formatDistanceToNow(new Date(sub.last_synced_at), {
                addSuffix: true,
              })
            : "—"}
        </span>
        <StatusBadge error={sub.sync_error} lastSynced={sub.last_synced_at} />
        <div className="min-w-24">
          <Select
            label="Sync interval"
            value={String(interval)}
            onValueChange={(v) => setInterval(Number(v))}
          >
            {INTERVALS.map(([m, short]) => (
              <Option key={m} value={String(m)}>
                {short}
              </Option>
            ))}
          </Select>
        </div>
        <IconButton
          aria-label={`Sync ${sub.title} now`}
          variant="ghost"
          size="sm"
          onClick={() => onSync(sub.id)}
          disabled={isSyncing}
        >
          <RefreshCw aria-hidden className="size-4" />
        </IconButton>
        <IconButton
          aria-label={`Delete ${sub.title}`}
          variant="ghost"
          size="sm"
          onClick={() => setShowDelete(true)}
        >
          <Trash2 aria-hidden className="size-4" />
        </IconButton>
      </div>

      <Modal
        open={showDelete}
        onClose={() => setShowDelete(false)}
        title={t("components.calendar.subscriptions.delete_confirm")}
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowDelete(false)}>
              {t("actions.cancel")}
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                onDelete(sub.id);
                setShowDelete(false);
              }}
            >
              {t("actions.delete")}
            </Button>
          </>
        }
      >
        <p className="text-sm">
          {t("components.calendar.subscriptions.delete_confirm_text", {
            title: sub.title,
          })}
        </p>
      </Modal>
    </>
  );
}
