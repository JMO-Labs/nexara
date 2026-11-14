"use client";
/**
 * @file components/notifications/NotifRow.tsx
 * @brief Registry-driven notification row with inline actions.
 */
import { useState } from "react";
import Link from "next/link";
import { Check } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";
import { Checkbox } from "@/components/ui/Checkbox";
import { IconButton } from "@/components/ui/IconButton";
import { cn } from "@/lib/utils";
import { safeInternalLink } from "@/lib/safeLink";
import { callAction, dismissOne } from "@/lib/api/notifications";
import { renderNotif } from "@/lib/notifications/renderers";
import type {
  NotificationItem,
  NotificationTypeDescriptor,
} from "@/lib/notifications/types";

export interface NotifRowProps {
  item: NotificationItem;
  type: NotificationTypeDescriptor;
  onDismissed: (id: string) => void;
  selected?: boolean;
  onSelectChange?: (id: string, selected: boolean) => void;
}

/**
 * @brief Notification row rendered through the type registry.
 * @param props see NotifRowProps
 * @return row element
 */
export function NotifRow({
  item,
  type,
  onDismissed,
  selected,
  onSelectChange,
}: NotifRowProps) {
  const t = useTranslations();
  const [pending, setPending] = useState<string | null>(null);
  const r = renderNotif(type, item.payload ?? {}, (k) => t(k));
  const link = safeInternalLink(r.link);
  const unread = !item.read_at && !item.dismissed_at;

  const handleAction = async (key: string) => {
    setPending(key);
    try {
      await callAction(item.id, key);
      onDismissed(item.id);
    } catch {
      /* keep row; user may retry */
    } finally {
      setPending(null);
    }
  };

  const ack = async () => {
    try {
      await dismissOne(item.id);
      onDismissed(item.id);
    } catch {
      /* keep row */
    }
  };

  const body = (
    <div
      data-testid="notif-row"
      data-unread={unread}
      className={cn(
        "border-ink/10 flex items-start gap-3 border-b px-4 py-3",
        unread && "bg-surface",
      )}
    >
      {onSelectChange && (
        <Checkbox
          aria-label="Select notification"
          checked={!!selected}
          onCheckedChange={(c) => onSelectChange(item.id, c === true)}
          onClick={(e) => e.stopPropagation()}
        />
      )}
      <div className="min-w-0 flex-1">
        <p className="text-muted text-xs">
          {new Date(item.created_at).toLocaleString()}
        </p>
        <p className="text-sm font-semibold">{r.title}</p>
        {r.body && <p className="text-sm break-words">{r.body}</p>}
        {r.actions.length > 0 && (
          <div className="mt-2 flex gap-2">
            {r.actions.map((a) => (
              <Button
                key={a.key}
                size="sm"
                variant={
                  a.style === "danger"
                    ? "destructive"
                    : a.style === "neutral"
                      ? "outline"
                      : "primary"
                }
                loading={pending === a.key}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  void handleAction(a.key);
                }}
              >
                {a.label}
              </Button>
            ))}
          </div>
        )}
      </div>
      {unread && (
        <IconButton
          aria-label="Acknowledge notification"
          size="sm"
          variant="ghost"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            void ack();
          }}
        >
          <Check aria-hidden width={16} height={16} />
        </IconButton>
      )}
    </div>
  );

  if (!link) return body;
  return (
    <Link
      href={link}
      className="focus-visible:ring-accent block text-inherit no-underline focus-visible:ring-2 focus-visible:outline-none focus-visible:ring-inset"
      onClick={() => void dismissOne(item.id).catch(() => undefined)}
    >
      {body}
    </Link>
  );
}
