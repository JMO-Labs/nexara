"use client";
/**
 * @file components/notifications/NotificationsDrawer.tsx
 * @brief Right-side drawer with notification history, All/Unread filters
 *        and bulk dismiss. Opens on the `notifications:drawer-open` event.
 */
import { useCallback, useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { dismissOne } from "@/lib/api/notifications";
import { useNotificationsSync } from "@/hooks/useNotificationsSync";
import {
  NotificationList,
  type NotificationFilter as Filter,
} from "./NotificationList";

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

  useEffect(() => {
    const onOpen = () => setOpen(true);
    window.addEventListener(DRAWER_OPEN_EVENT, onOpen);
    return () => window.removeEventListener(DRAWER_OPEN_EVENT, onOpen);
  }, []);

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
        <NotificationList
          filter={filter}
          enabled={open}
          selected={selected}
          onSelectChange={toggle}
        />
      </div>
    </Drawer>
  );
}
