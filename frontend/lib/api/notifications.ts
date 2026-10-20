/**
 * @file lib/api/notifications.ts
 * @brief Notification REST endpoints. The SSE stream is consumed via
 *        useSSE; these calls cover the imperative bits (list, count, mark).
 */
import { apiGet, apiPost, apiDelete, seg } from "./client";

export interface NotificationPayload {
  message?: string;
  link?: string;
  [key: string]: unknown;
}

export interface NotificationItem {
  id: string;
  user_id: string;
  type: string;
  payload: NotificationPayload;
  read_at: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  next_cursor: string | null;
  has_more: boolean;
}

export const listNotifications = (cursor?: string, limit = 20) => {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (cursor) qs.set("cursor", cursor);
  return apiGet<NotificationListResponse>(`/api/v1/notifications?${qs}`);
};

export const getUnreadCount = () =>
  apiGet<{ count: number }>("/api/v1/notifications/unread-count");

export const markRead = (id: string) =>
  apiPost<{ message: string }>(`/api/v1/notifications/${seg(id)}/read`);

export const markAllRead = () =>
  apiPost<{ message: string }>("/api/v1/notifications/read-all");

export const clearAllNotifications = () =>
  apiDelete<{ message: string }>("/api/v1/notifications");

export const STREAM_PATH = "/api/v1/notifications/stream";
