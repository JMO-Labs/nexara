/**
 * @file composables/usePushNotifications.ts
 * @brief Composable for Web Push notification management.
 *
 * Provides isSupported, permission, subscribe, unsubscribe, subscriptions,
 * and loading state. Uses GET /push/vapid-key, POST /push/subscribe,
 * DELETE /push/subscribe, GET /push/subscriptions.
 */

import { ref, computed } from "vue";
import { useApi } from "~/composables/useApi";
import type {
  VAPIDPublicKeyResponse,
  PushSubscriptionResponse,
} from "~/types/api";

/** @brief Base64 URL to Uint8Array. */
function urlBase64ToUint8Array(base64: string): Uint8Array {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const base64Url = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64Url);
  const arr = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
  return arr;
}

export function usePushNotifications() {
  const api = useApi();
  const loading = ref(false);
  const permission = ref<NotificationPermission>(
    typeof Notification !== "undefined" ? Notification.permission : "denied",
  );
  const subscriptions = ref<PushSubscriptionResponse[]>([]);

  const isSupported = computed(
    () =>
      typeof navigator !== "undefined" &&
      !!navigator.serviceWorker &&
      typeof PushManager !== "undefined",
  );

  async function fetchSubscriptions(): Promise<void> {
    if (!isSupported.value) return;
    try {
      const list = await api.get<PushSubscriptionResponse[]>(
        "/push/subscriptions",
      );
      subscriptions.value = list ?? [];
    } catch {
      subscriptions.value = [];
    }
  }

  async function subscribe(): Promise<boolean> {
    if (!isSupported.value) return false;
    loading.value = true;
    try {
      const perm =
        typeof Notification !== "undefined"
          ? await Notification.requestPermission()
          : "denied";
      permission.value = perm;
      if (perm !== "granted") return false;

      const reg = await navigator.serviceWorker.ready;
      const { public_key } = await api.get<VAPIDPublicKeyResponse>(
        "/push/vapid-key",
      );
      const applicationServerKey =
        urlBase64ToUint8Array(public_key).buffer as ArrayBuffer;
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey,
      });

      const keys = sub.getKey("p256dh");
      const auth = sub.getKey("auth");
      if (!keys || !auth) return false;

      await api.post("/push/subscribe", {
        endpoint: sub.endpoint,
        keys: {
          p256dh: btoa(String.fromCharCode(...new Uint8Array(keys))),
          auth: btoa(String.fromCharCode(...new Uint8Array(auth))),
        },
      });

      await fetchSubscriptions();
      return true;
    } catch {
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function unsubscribe(): Promise<void> {
    if (!isSupported.value) return;
    loading.value = true;
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (sub) {
        await api.del("/push/subscribe", { endpoint: sub.endpoint });
        await sub.unsubscribe();
      }
      await fetchSubscriptions();
    } catch {
      /* ignore */
    } finally {
      loading.value = false;
    }
  }

  return {
    isSupported,
    permission,
    subscribe,
    unsubscribe,
    subscriptions,
    loading,
    fetchSubscriptions,
  };
}
