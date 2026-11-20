"use client";
/**
 * @file components/notifications/NotificationList.tsx
 * @brief Notification history list shared by the drawer and /app/inbox.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { listNotifications } from "@/lib/api/notifications";
import { useNotificationRegistry } from "@/lib/notifications/registry";
import type { NotificationItem } from "@/lib/notifications/types";
import { NotifRow } from "./NotifRow";

export type NotificationFilter = "all" | "unread";

export interface NotificationListProps {
  filter: NotificationFilter;
  /** Selected notification ids; checkboxes show when onSelectChange is set. */
  selected?: Set<string>;
  onSelectChange?: (id: string, selected: boolean) => void;
  /** Fetch only when true (drawer passes its open state). */
  enabled?: boolean;
}

/**
 * @brief Filtered notification rows with empty state.
 * @param props see NotificationListProps
 * @return list element
 */
export function NotificationList({
  filter,
  selected,
  onSelectChange,
  enabled = true,
}: NotificationListProps) {
  const t = useTranslations();
  const qc = useQueryClient();
  const { byKey } = useNotificationRegistry();
  const { data } = useQuery({
    queryKey: ["notifications", "history"],
    queryFn: () => listNotifications(),
    enabled,
  });
  const all = (data?.items ?? []) as unknown as NotificationItem[];
  const items =
    filter === "unread"
      ? all.filter((n) => !n.read_at && !n.dismissed_at)
      : all;

  if (items.length === 0) {
    return (
      <p className="text-muted py-6 text-center text-sm">
        {t("notifications.drawer.empty")}
      </p>
    );
  }
  return (
    <div>
      {items.map((n) => {
        const type = byKey.get(n.type);
        if (!type) return null;
        return (
          <NotifRow
            key={n.id}
            item={n}
            type={type}
            selected={selected?.has(n.id)}
            onSelectChange={onSelectChange}
            onDismissed={() =>
              void qc.invalidateQueries({ queryKey: ["notifications"] })
            }
          />
        );
      })}
    </div>
  );
}
