'use client';
/**
 * @file hooks/usePushNotifications.ts
 * @brief Web Push subscription manager. Handles permission prompt, SW
 *        readiness, VAPID key fetch, browser pushManager.subscribe and
 *        backend POST /api/v1/push/subscribe round-trip. Idempotent —
 *        if an existing subscription is present we POST it again so the
 *        backend can refresh user-agent / created_at.
 */
import { useCallback, useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useMutationWithToast } from './useMutationWithToast';
import {
  getVapidKey,
  listPushSubscriptions,
  subscribePush,
  unsubscribePush,
  type PushSubscriptionResponse,
} from '@/lib/api/push';

export type PushPermission = 'default' | 'granted' | 'denied' | 'unsupported';

const SUBS_KEY = ['push', 'subscriptions'] as const;

function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4);
  const b64 = (base64 + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(b64);
  const buf = new ArrayBuffer(raw.length);
  const out = new Uint8Array(buf);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

function arrayBufferToBase64(buf: ArrayBuffer | null): string {
  if (!buf) return '';
  const bytes = new Uint8Array(buf);
  let s = '';
  for (let i = 0; i < bytes.byteLength; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function getPermission(): PushPermission {
  if (typeof window === 'undefined') return 'unsupported';
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return 'unsupported';
  return Notification.permission as PushPermission;
}

export function usePushNotifications() {
  const qc = useQueryClient();
  const [permission, setPermission] = useState<PushPermission>('default');

  useEffect(() => {
    // One-shot browser-capability sync; SSR can't read Notification.permission.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPermission(getPermission());
  }, []);

  const supported = permission !== 'unsupported';

  const subsQuery = useQuery({
    queryKey: SUBS_KEY,
    queryFn: listPushSubscriptions,
    enabled: supported,
    staleTime: 60_000,
  });

  const subscribeMutation = useMutationWithToast<PushSubscriptionResponse, Error, void>({
    mutationFn: async () => {
      if (!supported) throw new Error('Push not supported in this browser');
      let perm = Notification.permission as PushPermission;
      if (perm === 'default') {
        perm = (await Notification.requestPermission()) as PushPermission;
        setPermission(perm);
      }
      if (perm !== 'granted') throw new Error('Permission denied');

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
      const p256dh = json.keys?.p256dh ?? arrayBufferToBase64(sub.getKey('p256dh'));
      const auth = json.keys?.auth ?? arrayBufferToBase64(sub.getKey('auth'));
      return subscribePush({ endpoint: sub.endpoint, keys: { p256dh, auth } });
    },
    successKey: 'toasts.settings.saved',
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SUBS_KEY });
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
    successKey: 'toasts.settings.saved',
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SUBS_KEY });
    },
  });

  const subscribe = useCallback(() => subscribeMutation.mutateAsync(), [subscribeMutation]);
  const unsubscribe = useCallback(() => unsubscribeMutation.mutateAsync(), [unsubscribeMutation]);

  const isSubscribed = (subsQuery.data?.length ?? 0) > 0;

  return {
    supported,
    permission,
    isSubscribed,
    subscriptions: subsQuery.data ?? [],
    isLoading: subsQuery.isLoading,
    subscribe,
    unsubscribe,
    isSubscribing: subscribeMutation.isPending,
    isUnsubscribing: unsubscribeMutation.isPending,
    error: subscribeMutation.error ?? unsubscribeMutation.error ?? null,
  };
}
