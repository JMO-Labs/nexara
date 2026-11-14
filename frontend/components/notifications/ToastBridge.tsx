"use client";
/**
 * @file components/notifications/ToastBridge.tsx
 * @brief Bridges SSE notification events to the toast queue for types
 *        whose descriptor sets toast_on_arrival. Renders nothing.
 */
import { useTranslations } from "next-intl";
import { useSSE } from "@/hooks/useSSE";
import { dismissOne, STREAM_PATH } from "@/lib/api/notifications";
import { useNotificationRegistry } from "@/lib/notifications/registry";
import { renderNotif, type Translate } from "@/lib/notifications/renderers";
import { useToasts } from "@/stores/toasts";

interface StreamEvent {
  type: string;
  id?: string;
  payload?: Record<string, unknown>;
}

/** @brief Mount once inside the authenticated shell. @return null */
export function ToastBridge() {
  const t = useTranslations();
  const push = useToasts((s) => s.push);
  const { byKey } = useNotificationRegistry();

  useSSE(STREAM_PATH, {
    eventTypes: ["user_notification", "user_toast"],
    onMessage: (data) => {
      const evt = data as StreamEvent;
      const desc = byKey.get(evt?.type);
      if (!desc || !desc.toast_on_arrival) return;
      const r = renderNotif(desc, evt.payload ?? {}, t as unknown as Translate);
      const link = r.link;
      push({
        variant: desc.bypass_dnd ? "warning" : "info",
        title: r.title,
        message: r.body,
        dedupeKey: evt.id ? `notif:${evt.id}` : undefined,
        action: link
          ? {
              label: t("notifications.toast.open"),
              onClick: () => {
                if (evt.id) dismissOne(evt.id).catch(() => {});
                window.location.assign(link);
              },
            }
          : undefined,
      });
    },
  });
  return null;
}
