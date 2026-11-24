"use client";
/**
 * @file hooks/usePushNotifications.ts
 * @brief Web Push subscription manager. Handles permission prompt (isSubscribed = this device's endpoint hash is in /push/devices), SW
 *        readiness, VAPID key fetch, browser pushManager.subscribe and
 *        backend POST /api/v1/push/subscribe round-trip. Idempotent —
 *        if an existing subscription is present we POST it again so the
 *        backend can refresh user-agent / created_at.
 */
import { useCallback, useState, useSyncExternalStore } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMutationWithToast } from "./useMutationWithToast";
import {
  getVapidKey,
  listPushDevices,
  subscribePush,
  unsubscribePush,
  type PushSubscriptionResponse,
} from "@/lib/api/push";

export type PushPermission = "default" | "granted" | "denied" | "unsupported";

const SUBS_KEY = ["push", "devices"] as const;
const LOCAL_KEY = ["push", "local-hash"] as const;

/** @brief sha256(endpoint) hex, first 16 chars (matches backend endpoint_hash). */
export async function endpointHash(endpoint: string): Promise<string> {
  const d = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(endpoint),
  );
  return [...new Uint8Array(d)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, 16);
}

/** @brief Hash of this browser's current push endpoint, or null. */
async function localHash(): Promise<string | null> {
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  return sub ? endpointHash(sub.endpoint) : null;
}

function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const b64 = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(b64);
  const buf = new ArrayBuffer(raw.length);
  const out = new Uint8Array(buf);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

function arrayBufferToBase64(buf: ArrayBuffer | null): string {
  if (!buf) return "";
  const bytes = new Uint8Array(buf);
  let s = "";
  for (let i = 0; i < bytes.byteLength; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function getPermission(): PushPermission {
  if (typeof window === "undefined") return "unsupported";
  if (!("serviceWorker" in navigator) || !("PushManager" in window))
    return "unsupported";
  return Notification.permission as PushPermission;
}

/** @brief No-op subscribe: permission changes are tracked via local state. */
const noopSubscribe = () => () => {};

export function usePushNotifications() {
  const qc = useQueryClient();
  // Browser permission read as an external store; SSR snapshot is "default".
  const browserPermission = useSyncExternalStore(
    noopSubscribe,
    getPermission,
    () => "default" as PushPermission,
  );
  const [requested, setPermission] = useState<PushPermission | null>(null);
  const permission = requested ?? browserPermission;

  const supported = permission !== "unsupported";

  const subsQuery = useQuery({
    queryKey: SUBS_KEY,
    queryFn: listPushDevices,
    enabled: supported,
    staleTime: 60_000,
  });
  const localQuery = useQuery({
    queryKey: LOCAL_KEY,
    queryFn: localHash,
    enabled: supported,
    staleTime: 60_000,
  });

  const subscribeMutation = useMutationWithToast<
    PushSubscriptionResponse,
    Error,
    void
  >({
    mutationFn: async () => {
      if (!supported) throw new Error("Push not supported in this browser");
      let perm = Notification.permission as PushPermission;
      if (perm === "default") {
        perm = (await Notification.requestPermission()) as PushPermission;
        setPermission(perm);
      }
      if (perm !== "granted") throw new Error("Permission denied");

      const reg = await navigator.serviceWorker.ready;
      const { public_key } = await getVapidKey();
      const existing = await reg.pushManager.getSubscription();
      const sub =
        existing ??
        (await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(public_key),
        }));
      const json = sub.toJSON() as {
        endpoint: string;
        keys?: { p256dh?: string; auth?: string };
      };
      const p256dh =
        json.keys?.p256dh ?? arrayBufferToBase64(sub.getKey("p256dh"));
      const auth = json.keys?.auth ?? arrayBufferToBase64(sub.getKey("auth"));
      return subscribePush({ endpoint: sub.endpoint, keys: { p256dh, auth } });
    },
    successKey: "toasts.settings.saved",
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["push"] });
    },
  });

  const unsubscribeMutation = useMutationWithToast<void, Error, void>({
    mutationFn: async () => {
      if (!supported) return;
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (!sub) return;
      try {
        await unsubscribePush(sub.endpoint);
      } finally {
        await sub.unsubscribe();
      }
    },
    successKey: "toasts.settings.saved",
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["push"] });
    },
  });

  const subscribe = useCallback(
    () => subscribeMutation.mutateAsync(),
    [subscribeMutation],
  );
  const unsubscribe = useCallback(
    () => unsubscribeMutation.mutateAsync(),
    [unsubscribeMutation],
  );

  const thisHash = localQuery.data ?? null;
  const isSubscribed =
    !!thisHash && !!subsQuery.data?.some((d) => d.endpoint_hash === thisHash);

  return {
    supported,
    permission,
    isSubscribed,
    devices: subsQuery.data ?? [],
    thisHash,
    isLoading: subsQuery.isLoading || localQuery.isLoading,
    subscribe,
    unsubscribe,
    isSubscribing: subscribeMutation.isPending,
    isUnsubscribing: unsubscribeMutation.isPending,
    error: subscribeMutation.error ?? unsubscribeMutation.error ?? null,
  };
}
