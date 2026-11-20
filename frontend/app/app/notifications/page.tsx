"use client";
/**
 * @file app/app/notifications/page.tsx
 * @brief Notifications page: All/Unread filter, mark all read, shared list.
 */
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";
import { Panel, PageHeader, Segmented, Toolbar } from "@/components/ui/page";
import {
  NotificationList,
  type NotificationFilter,
} from "@/components/notifications/NotificationList";
import { useNotificationsSync } from "@/hooks/useNotificationsSync";
import { markAllRead } from "@/lib/api/notifications";

/** @brief Notifications route. */
export default function NotificationsPage() {
  const t = useTranslations("notifications");
  const qc = useQueryClient();
  useNotificationsSync();
  const [filter, setFilter] = useState<NotificationFilter>("all");
  const markAll = useMutation({
    mutationFn: markAllRead,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
  return (
    <>
      <PageHeader
        title={t("title")}
        actions={
          <Button
            variant="secondary"
            loading={markAll.isPending}
            onClick={() => markAll.mutate()}
          >
            {t("markAllRead")}
          </Button>
        }
      />
      <Toolbar>
        <Segmented
          label={t("title")}
          value={filter}
          onChange={setFilter}
          options={[
            { value: "all", label: t("filter.all") },
            { value: "unread", label: t("filter.unread") },
          ]}
        />
      </Toolbar>
      <Panel>
        <NotificationList filter={filter} />
      </Panel>
    </>
  );
}
