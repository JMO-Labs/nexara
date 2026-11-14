"use client";
/**
 * @file components/notifications/NotificationsDrawer.tsx
 * @brief Right-side drawer with notification history, All/Unread filters
 *        and bulk dismiss. Opens on the `notifications:drawer-open` event.
 */
import { useCallback, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { dismissOne, listNotifications } from "@/lib/api/notifications";
import { useNotificationRegistry } from "@/lib/notifications/registry";
import type { NotificationItem } from "@/lib/notifications/types";
import { useNotificationsSync } from "@/hooks/useNotificationsSync";
import { NotifRow } from "./NotifRow";

type Filter = "all" | "unread";

/** @brief Event name that opens the drawer. */
export const DRAWER_OPEN_EVENT = "notifications:drawer-open";

/**
 * @brief Notifications history drawer.
 * @return drawer element
 */
export function NotificationsDrawer() {
  const t = useTranslations();
  const qc = useQueryClient();
  useNotificationsSync();
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState<Filter>("all");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const { byKey } = useNotificationRegistry();

  useEffect(() => {
    const onOpen = () => setOpen(true);
    window.addEventListener(DRAWER_OPEN_EVENT, onOpen);
    return () => window.removeEventListener(DRAWER_OPEN_EVENT, onOpen);
  }, []);

  const { data } = useQuery({
    queryKey: ["notifications", "history"],
    queryFn: () => listNotifications(),
    enabled: open,
  });

  const invalidate = useCallback(() => {
    void qc.invalidateQueries({ queryKey: ["notifications"] });
  }, [qc]);

  const bulk = useMutation({
    mutationFn: (ids: string[]) =>
      Promise.allSettled(ids.map((id) => dismissOne(id))),
    onSuccess: () => {
      setSelected(new Set());
      invalidate();
    },
  });

  const all = (data?.items ?? []) as unknown as NotificationItem[];
  const items =
    filter === "unread"
      ? all.filter((n) => !n.read_at && !n.dismissed_at)
      : all;

  const toggle = (id: string, on: boolean) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });

  const chip = (f: Filter, label: string) => (
    <Button
      size="sm"
      variant={filter === f ? "primary" : "outline"}
      aria-pressed={filter === f}
      onClick={() => setFilter(f)}
    >
      {label}
    </Button>
  );

  return (
    <Drawer
      open={open}
      onClose={() => setOpen(false)}
      title={t("notifications.drawer.title")}
    >
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          {chip("all", t("notifications.filter.all"))}
          {chip("unread", t("notifications.filter.unread"))}
          {selected.size > 0 && (
            <Button
              size="sm"
              variant="destructive"
              className="ml-auto"
              loading={bulk.isPending}
              onClick={() => bulk.mutate([...selected])}
            >
              {t("notifications.bulk.dismiss")}
            </Button>
          )}
        </div>
        {items.length === 0 ? (
          <p className="text-muted py-6 text-center text-sm">
            {t("notifications.drawer.empty")}
          </p>
        ) : (
          <div>
            {items.map((n) => {
              const type = byKey.get(n.type);
              if (!type) return null;
              return (
                <NotifRow
                  key={n.id}
                  item={n}
                  type={type}
                  selected={selected.has(n.id)}
                  onSelectChange={toggle}
                  onDismissed={invalidate}
                />
              );
            })}
          </div>
        )}
      </div>
    </Drawer>
  );
}
