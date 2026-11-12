"use client";
/**
 * @file components/events/subscriptions/SubscriptionRow.tsx
 * @brief Single calendar subscription row with sync interval, sync, delete.
 */
import * as React from "react";
import { Pencil, RefreshCw, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { formatDistanceToNow } from "date-fns";
import {
  Button,
  IconButton,
  Modal,
  Select,
  Option,
  Switch,
} from "@/components/ui";
import type {
  CalendarSubscription,
  UpdateSubscriptionBody,
} from "@/lib/api/events";
import { StatusBadge } from "./StatusBadge";
import { INTERVALS } from "./intervals";
import { AddModal } from "./AddModal";

export interface SubscriptionRowProps {
  sub: CalendarSubscription;
  onDelete: (id: string) => void;
  onSync: (id: string) => void;
  onUpdate: (id: string, body: UpdateSubscriptionBody) => void;
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
  onUpdate,
  isSyncing,
}: SubscriptionRowProps) {
  const t = useTranslations();
  const [showDelete, setShowDelete] = React.useState(false);
  const [showEdit, setShowEdit] = React.useState(false);

  return (
    <>
      <div className="grid grid-cols-[1fr_auto] items-center gap-x-2 gap-y-1 border-b border-current/15 px-4 py-3 last:border-b-0 hover:bg-bg md:grid-cols-[1fr_1.2fr_1fr_0.8fr_0.9fr_auto_auto_auto_auto]">
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
            value={String(sub.sync_interval_minutes)}
            onValueChange={(v) =>
              onUpdate(sub.id, { sync_interval_minutes: Number(v) })
            }
          >
            {INTERVALS.map(([m, short]) => (
              <Option key={m} value={String(m)}>
                {short}
              </Option>
            ))}
          </Select>
        </div>
        <Switch
          aria-label={`Sync ${sub.title} enabled`}
          checked={sub.sync_enabled ?? true}
          onCheckedChange={(v: boolean) =>
            onUpdate(sub.id, { sync_enabled: v })
          }
        />
        <IconButton
          aria-label={`Edit ${sub.title}`}
          variant="ghost"
          size="sm"
          onClick={() => setShowEdit(true)}
        >
          <Pencil aria-hidden className="size-4" />
        </IconButton>
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

      <AddModal
        open={showEdit}
        onClose={() => setShowEdit(false)}
        initial={sub}
        isLoading={false}
        onSubmit={(d) => {
          onUpdate(sub.id, d);
          setShowEdit(false);
        }}
      />

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
