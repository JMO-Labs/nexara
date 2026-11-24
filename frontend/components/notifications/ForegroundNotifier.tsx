"use client";
/**
 * @file components/notifications/ForegroundNotifier.tsx
 * @brief When the tab is hidden, granted, and this device has no Web Push
 *        subscription, shows SSE notifications as OS notifications.
 *        Renders nothing.
 */
import { useTranslations } from "next-intl";
import { useSSE } from "@/hooks/useSSE";
import { usePushNotifications } from "@/hooks/usePushNotifications";
import { STREAM_PATH } from "@/lib/api/notifications";
import { useNotificationRegistry } from "@/lib/notifications/registry";
import { renderNotif, type Translate } from "@/lib/notifications/renderers";

interface StreamEvent {
  type: string;
  id?: string;
  payload?: Record<string, unknown>;
}

/** @brief Mount once inside the authenticated shell. @return null */
export function ForegroundNotifier() {
  const t = useTranslations();
  const { byKey } = useNotificationRegistry();
  const { isSubscribed } = usePushNotifications();

  useSSE(STREAM_PATH, {
    eventTypes: ["user_notification"],
    onMessage: async (data) => {
      if (document.visibilityState !== "hidden" || isSubscribed) return;
      if (typeof Notification === "undefined") return;
      if (Notification.permission !== "granted") return;
      const evt = data as StreamEvent;
      const desc = byKey.get(evt?.type);
      if (!desc) return;
      const r = renderNotif(desc, evt.payload ?? {}, t as unknown as Translate);
      try {
        const reg = await navigator.serviceWorker.ready;
        await reg.showNotification(r.title, {
          body: r.body,
          icon: "/icons/icon-192.png",
          badge: "/icons/badge-72.png",
          tag: evt.type,
          data: { url: r.link ?? "/app" },
        });
      } catch {
        /* no SW / blocked: nothing to show */
      }
    },
  });
  return null;
}
