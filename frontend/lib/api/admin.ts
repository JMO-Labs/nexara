/**
 * @file lib/api/admin.ts
 * @brief Admin panel API endpoints covering metrics, user management,
 *        settings, and audit logging.
 */
import { apiGet, apiPost, apiPut, apiDelete, seg } from "./client";

/**
 * @brief Community-level activity metrics.
 */
export interface CommunityMetrics {
  users_total: number;
  users_active_30d: number;
  users_online_now: number;
  posts_total: number;
  posts_last_7d: number;
  media_files: number;
  media_storage_bytes: number;
}

/**
 * @brief System health metrics.
 */
export interface SystemMetrics {
  version: string;
  uptime_seconds: number;
  db_size_bytes?: number | null;
  valkey_memory_bytes?: number | null;
  celery_queue_depth?: number | null;
}

/**
 * @brief WAF block metrics.
 */
export interface WafMetrics {
  blocks_today: number;
  blocks_by_reason: Record<string, number>;
}

/**
 * @brief Combined metrics response.
 */
export interface MetricsResponse {
  community: CommunityMetrics;
  system: SystemMetrics;
  waf: WafMetrics;
}

/**
 * @brief Admin user list item.
 */
export interface AdminUserListItem {
  id: string;
  username: string;
  display_name: string;
  email: string;
  avatar_url: string | null;
  bio: string | null;
  title: string | null;
  location: string | null;
  website_url: string | null;
  role: string;
  created_at: Date;
  last_seen_at: Date | null;
  status: string;
}

/**
 * @brief Paginated response envelope.
 */
export interface PaginatedResponse<T> {
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
}

/**
 * @brief Message response.
 */
export interface MessageResponse {
  message: string;
}

/**
 * @brief Admin settings.
 */
export interface AdminSettingsResponse {
  enable_registration: boolean;
  require_invite: boolean;
  storage_quota_default: number;
  waf_enabled: boolean;
}

/**
 * @brief Admin settings update payload.
 */
export interface AdminSettingsUpdate {
  enable_registration?: boolean;
  require_invite?: boolean;
  storage_quota_default?: number;
  waf_enabled?: boolean;
}

/**
 * @brief Audit log entry.
 */
export interface AuditLogEntry {
  id: string;
  actor_id: string | null;
  actor_display_name: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  target_display: string | null;
  extra_data: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: Date;
}

/**
 * @brief Fetch community, system, and WAF metrics.
 * @return MetricsResponse
 */
export const getMetrics = () =>
  apiGet<MetricsResponse>("/api/v1/admin/metrics");

/**
 * @brief List admin users with optional search and pagination.
 * @param filters Optional query filters: q, limit, cursor
 * @return PaginatedResponse of AdminUserListItem
 */
export const listAdminUsers = (filters?: {
  q?: string;
  limit?: number;
  cursor?: string | null;
}) => {
  const qs = new URLSearchParams();
  if (filters?.q) qs.set("q", filters.q);
  if (filters?.limit) qs.set("limit", String(filters.limit));
  if (filters?.cursor) qs.set("cursor", filters.cursor);
  return apiGet<PaginatedResponse<AdminUserListItem>>(
    `/api/v1/admin/users?${qs}`,
  );
};

/**
 * @brief Change a user's role.
 * @param userId User ID
 * @param role New role: admin, member, or viewer
 * @return MessageResponse
 */
export const changeUserRole = (userId: string, role: string) =>
  apiPut<MessageResponse>(`/api/v1/admin/users/${seg(userId)}/role`, { role });

/**
 * @brief Suspend a user.
 * @param userId User ID
 * @return MessageResponse
 */
export const suspendUser = (userId: string) =>
  apiPost<MessageResponse>(`/api/v1/admin/users/${seg(userId)}/suspend`);

/**
 * @brief Restore a suspended user.
 * @param userId User ID
 * @return MessageResponse
 */
export const restoreUser = (userId: string) =>
  apiPost<MessageResponse>(`/api/v1/admin/users/${seg(userId)}/restore`);

/**
 * @brief Delete a user.
 * @param userId User ID
 * @return MessageResponse
 */
export const deleteUser = (userId: string) =>
  apiDelete<MessageResponse>(`/api/v1/admin/users/${seg(userId)}`);

/**
 * @brief Fetch admin settings.
 * @return AdminSettingsResponse
 */
export const getAdminSettings = () =>
  apiGet<AdminSettingsResponse>("/api/v1/admin/settings");

/**
 * @brief Update admin settings (partial).
 * @param updates Partial settings object
 * @return AdminSettingsResponse
 */
export const updateAdminSettings = (updates: AdminSettingsUpdate) =>
  apiPut<AdminSettingsResponse>("/api/v1/admin/settings", updates);

/**
 * @brief List audit log entries.
 * @param filters Optional pagination: limit, cursor
 * @return PaginatedResponse of AuditLogEntry
 */
export const getAuditLog = (filters?: {
  limit?: number;
  cursor?: string | null;
}) => {
  const qs = new URLSearchParams();
  if (filters?.limit) qs.set("limit", String(filters.limit));
  if (filters?.cursor) qs.set("cursor", filters.cursor);
  return apiGet<PaginatedResponse<AuditLogEntry>>(
    `/api/v1/admin/audit-log?${qs}`,
  );
};
