/**
 * @file stores/notifications.ts
 * @brief Pinia store for notification management.
 *
 * Manages in-app notifications: fetch list, unread count, mark read.
 * Uses useApi() for all HTTP calls to /notifications/ endpoints.
 */

import { ref } from "vue";
import { defineStore } from "pinia";
import { useApi } from "~/composables/useApi";
import { useEventBus } from "~/composables/useEventBus";
import { SSE_EVENT } from "~/types/events";
import type {
  Notification,
  NotificationListResponse,
  UnreadCountResponse,
} from "~/types/api";

export const useNotificationsStore = defineStore("notifications", () => {
  /** @brief List of notifications from the API. */
  const notifications = ref<Notification[]>([]);

  /** @brief Unread notification count for badge display. */
  const unreadCount = ref(0);

  /** @brief Whether a fetch operation is in progress. */
  const loading = ref(false);

  /**
   * @brief Fetch notifications from GET /notifications/.
   * @param cursor - Optional pagination cursor.
   * @throws Error if the request fails.
   */
  async function fetchNotifications(cursor?: string | null): Promise<void> {
    loading.value = true;
    try {
      const api = useApi();
      const params = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
      const data = await api.get<NotificationListResponse>(
        `/notifications/${params}`,
      );
      if (cursor) {
        notifications.value = [...notifications.value, ...data.items];
      } else {
        notifications.value = data.items;
      }
    } finally {
      loading.value = false;
    }
  }

  /**
   * @brief Fetch unread count from GET /notifications/unread-count.
   * @throws Error if the request fails.
   */
  async function fetchUnreadCount(): Promise<void> {
    const api = useApi();
    const data = await api.get<UnreadCountResponse>(
      "/notifications/unread-count",
    );
    unreadCount.value = data.count;
  }

  /**
   * @brief Mark a notification as read via POST /notifications/{id}/read.
   * @param id - Notification UUID.
   * @throws Error if the request fails.
   */
  async function markRead(id: string): Promise<void> {
    const api = useApi();
    await api.post(`/notifications/${id}/read`);
    const n = notifications.value.find((x) => x.id === id);
    if (n && !n.read_at) {
      n.read_at = new Date().toISOString();
      unreadCount.value = Math.max(0, unreadCount.value - 1);
    }
  }

  /**
   * @brief Mark all notifications as read via POST /notifications/read-all.
   * @throws Error if the request fails.
   */
  async function markAllRead(): Promise<void> {
    const api = useApi();
    await api.post("/notifications/read-all");
    notifications.value.forEach((n) => {
      if (!n.read_at) n.read_at = new Date().toISOString();
    });
    unreadCount.value = 0;
  }

  /**
   * @brief Delete all notifications via DELETE /notifications/.
   * @throws Error if the request fails.
   */
  async function clearAll(): Promise<void> {
    const api = useApi();
    await api.del("/notifications/");
    notifications.value = [];
    unreadCount.value = 0;
  }

  /**
   * @brief Handle an incoming SSE notification event.
   *
   * Prepends the notification to the list and increments unread count.
   * @param data - Raw notification payload from SSE.
   */
  function handleIncoming(data: Notification): void {
    if (notifications.value.some((n) => n.id === data.id)) return;
    notifications.value.unshift(data);
    if (!data.read_at) {
      unreadCount.value++;
    }
  }

  const { on } = useEventBus();
  on(SSE_EVENT.NOTIFICATION, (data) =>
    handleIncoming(data as Notification),
  );

  return {
    notifications,
    unreadCount,
    loading,
    fetchNotifications,
    fetchUnreadCount,
    markRead,
    markAllRead,
    clearAll,
    handleIncoming,
  };
});
