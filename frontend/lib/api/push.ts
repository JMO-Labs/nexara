/**
 * @file lib/api/push.ts
 * @brief Web Push API client. Mirrors backend/app/api/v1/push.py contract:
 *        VAPID key fetch, subscribe (POST), unsubscribe (DELETE w/ body),
 *        list subscriptions.
 */
import { apiGet, apiPost, apiPatch, apiDelete, api, seg } from "./client";

export interface VAPIDPublicKeyResponse {
  public_key: string;
}

export interface PushSubscribeRequest {
  endpoint: string;
  keys: { p256dh: string; auth: string };
}

export interface PushSubscriptionResponse {
  id: string;
  endpoint: string;
  user_agent: string | null;
  created_at: string;
}

export const getVapidKey = () =>
  apiGet<VAPIDPublicKeyResponse>("/api/v1/push/vapid-key");

export const subscribePush = (body: PushSubscribeRequest) =>
  apiPost<PushSubscriptionResponse>("/api/v1/push/subscribe", body);

export const unsubscribePush = (endpoint: string) =>
  api<{ message: string }>("/api/v1/push/subscribe", {
    method: "DELETE",
    body: { endpoint },
  });

export interface PushDevice {
  id: string;
  name: string;
  /** sha256(endpoint) hex, first 16 chars. */
  endpoint_hash: string;
  created_at: string;
  last_used_at: string | null;
}

export const listPushDevices = () =>
  apiGet<PushDevice[]>("/api/v1/push/devices");

export const renamePushDevice = (id: string, name: string) =>
  apiPatch<PushDevice>(`/api/v1/push/devices/${seg(id)}`, { name });

export const removePushDevice = (id: string) =>
  apiDelete(`/api/v1/push/devices/${seg(id)}`);
