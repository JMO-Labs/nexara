/**
 * @file lib/api/webhooks.ts
 * @brief Notification webhook subscriptions (per-user and per-community).
 */
import { apiGet, apiPost, apiPatch, apiDelete, seg } from "./client";
import type {
  WebhookCreateBody,
  WebhookCreateResponse,
  WebhookListItem,
  WebhookUpdateBody,
} from "@/lib/notifications/types";

const USER_BASE = "/api/v1/notifications/webhooks";
const communityBase = (id: string) => `/api/v1/communities/${seg(id)}/webhooks`;

export const listWebhooks = () => apiGet<WebhookListItem[]>(USER_BASE);

export const createWebhook = (body: WebhookCreateBody) =>
  apiPost<WebhookCreateResponse>(USER_BASE, body);

export const updateWebhook = (id: string, body: WebhookUpdateBody) =>
  apiPatch<WebhookListItem>(`${USER_BASE}/${seg(id)}`, body);

export const deleteWebhook = (id: string) =>
  apiDelete<{ message: string }>(`${USER_BASE}/${seg(id)}`);

export const listCommunityWebhooks = (communityId: string) =>
  apiGet<WebhookListItem[]>(communityBase(communityId));

export const createCommunityWebhook = (
  communityId: string,
  body: WebhookCreateBody,
) => apiPost<WebhookCreateResponse>(communityBase(communityId), body);
