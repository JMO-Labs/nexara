/**
 * @file lib/api/push.ts
 * @brief Web Push API client. Mirrors backend/app/api/v1/push.py contract:
 *        VAPID key fetch, subscribe (POST), unsubscribe (DELETE w/ body),
 *        list subscriptions.
 */
import { apiGet, apiPost, api } from "./client";

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

export const listPushSubscriptions = () =>
  apiGet<PushSubscriptionResponse[]>("/api/v1/push/subscriptions");
