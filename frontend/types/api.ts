/**
 * @file types/api.ts
 * @brief TypeScript types for the Nexara backend API.
 *
 * These types mirror the backend Pydantic schemas and are used by
 * stores, composables, and components to ensure type safety across
 * the frontend. In a production workflow these would be auto-generated
 * from the OpenAPI schema via `openapi-typescript`.
 */

/** @brief User roles matching backend RBAC. */
export type UserRole = "admin" | "member" | "viewer";

/**
 * @brief Authenticated user profile returned by GET /users/me.
 *
 * Mirrors backend `UserDetailResponse` schema.
 */
export interface User {
  id: string;
  email: string;
  username: string;
  display_name: string;
  email_verified: boolean;
  avatar_url: string | null;
  bio: string | null;
  title: string | null;
  location: string | null;
  website_url: string | null;
  birthday: string | null;
  role: UserRole;
  totp_enabled: boolean;
  storage_used: number;
  storage_quota: number;
  created_at: string;
  updated_at: string;
  last_seen_at: string | null;
}

/** @brief Login request payload. */
export interface LoginRequest {
  email: string;
  password: string;
}

/**
 * @brief Login/register response from the backend.
 *
 * Mirrors backend `LoginResponse` schema. The user profile is NOT included;
 * the client must call GET /users/me separately after obtaining a token.
 * When `requires_2fa` is true, `access_token` is null and the client
 * must complete the 2FA flow with `two_factor_token`.
 */
export interface LoginResponse {
  access_token: string | null;
  token_type: string;
  expires_in: number | null;
  requires_2fa: boolean;
  two_factor_token: string | null;
}

/** @brief Token refresh response (same shape as LoginResponse). */
export interface RefreshResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

/** @brief Registration request payload. */
export interface RegisterRequest {
  email: string;
  username: string;
  display_name: string;
  password: string;
  invite_token?: string;
}

/** @brief Post author summary embedded in post responses. */
export interface PostAuthor {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
}

/** @brief Media attachment on a post. */
export interface PostMedia {
  id: string;
  url: string;
  thumbnail_url: string | null;
  mime_type: string;
  width: number | null;
  height: number | null;
}

/** @brief Reaction summary for a post. */
export interface Reaction {
  emoji: string;
  count: number;
  reacted_by_me: boolean;
}

/** @brief Comment on a post. */
export interface Comment {
  id: string;
  content: string;
  author: PostAuthor;
  parent_id: string | null;
  created_at: string;
  reactions: Reaction[];
  replies?: Comment[];
}

/** @brief Full post object returned by the feed API. */
export interface Post {
  id: string;
  content: string;
  author: PostAuthor;
  media: PostMedia[];
  reactions: Reaction[];
  comment_count: number;
  created_at: string;
  updated_at: string;
}

/** @brief Cursor-paginated response wrapper. */
export interface PaginatedResponse<T> {
  items: T[];
  cursor: string | null;
  has_more: boolean;
}

/** @brief Standard API error envelope. */
export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

/**
 * @brief User settings response from GET /settings/.
 *
 * Mirrors backend settings schema. Includes notification preferences
 * and display preferences (theme, locale).
 */
export interface UserSettingsResponse {
  notif_mention_inapp: boolean;
  notif_mention_email: boolean;
  notif_comment_inapp: boolean;
  notif_comment_email: boolean;
  notif_reaction_inapp: boolean;
  notif_reaction_email: boolean;
  notif_new_post_inapp: boolean;
  notif_new_post_email: boolean;
  notif_system_inapp: boolean;
  notif_system_email: boolean;
  notif_invite_accepted_inapp: boolean;
  notif_invite_accepted_email: boolean;
  mute_all_email: boolean;
  theme: string;
  locale: string;
}

/**
 * @brief Single notification from GET /notifications/.
 *
 * Mirrors backend NotificationResponse schema.
 */
export interface Notification {
  id: string;
  user_id: string;
  type: string;
  payload: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
}

/**
 * @brief Paginated notification list response.
 *
 * Mirrors backend NotificationList schema.
 */
export interface NotificationListResponse {
  items: Notification[];
  next_cursor: string | null;
  has_more: boolean;
}

/** @brief Unread count from GET /notifications/unread-count. */
export interface UnreadCountResponse {
  count: number;
}

/** @brief Toast notification item in UI store. */
export interface ToastItem {
  id: string;
  type: "success" | "error" | "info" | "warning";
  message: string;
  duration?: number;
}

/** @brief Single search result item. */
export interface SearchResultItem {
  id: string;
  type: "posts" | "users" | "events" | "comments";
  title: string;
  snippet: string;
  created_at: string;
  /** @brief Parent entity ID (e.g. post_id for comment results). */
  parent_id?: string | null;
}

/** @brief Paginated results for one content type. */
export interface SearchTypeResults {
  items: SearchResultItem[];
  total: number;
  next_cursor: string | null;
}

/** @brief Full search API response. */
export interface SearchResponse {
  query: string;
  results: Record<string, SearchTypeResults>;
}

/** @brief Admin metrics response from GET /admin/metrics (flat, for UI). */
export interface AdminMetricsResponse {
  total_users: number;
  active_users_30d: number;
  online_now: number;
  total_posts: number;
  posts_7d: number;
  media_files: number;
  storage_used_bytes: number;
  waf_blocks_total?: number;
}

/**
 * @brief Raw metrics API response (nested structure from backend).
 *
 * Backend returns { community, system, waf }; map to AdminMetricsResponse in UI.
 */
export interface AdminMetricsApiResponse {
  community: {
    users_total: number;
    users_active_30d: number;
    users_online_now: number;
    posts_total: number;
    posts_last_7d: number;
    media_files: number;
    media_storage_bytes: number;
  };
  system: Record<string, unknown>;
  waf: { blocks_today: number; blocks_by_reason: Record<string, number> };
}

/** @brief Audit log entry from GET /admin/audit-log. */
export interface AuditLogEntry {
  id: string;
  actor_id: string | null;
  actor_display_name?: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  target_display?: string | null;
  ip_address: string | null;
  created_at: string;
}

/** @brief Paginated audit log response. */
export interface AuditLogResponse {
  items: AuditLogEntry[];
  next_cursor: string | null;
  has_more: boolean;
}

/** @brief Admin user list item (extended User). */
export interface AdminUserListItem extends User {
  status?: "active" | "suspended";
}

/** @brief Paginated admin users response. */
export interface AdminUsersResponse {
  items: AdminUserListItem[];
  total: number;
  cursor?: string | null;
  has_more?: boolean;
}

/** @brief Invite list item from GET /admin/invites. */
export interface InviteListItem {
  id: string;
  email: string;
  role: string;
  created_at: string;
  expires_at: string;
  used_at: string | null;
  status: "active" | "used" | "expired";
}

/** @brief Community settings from GET/PUT /admin/settings. */
export interface AdminCommunitySettings {
  enable_registration: boolean;
  require_invite: boolean;
  default_storage_quota_mb: number;
  waf_enabled: boolean;
}

/** @brief OAuth provider info for login page buttons. */
export interface OAuthProviderInfo {
  slug: string;
  display_name: string;
  icon_url: string | null;
}

/** @brief Group mapping: IdP group name -> Nexara role. */
export interface OAuthGroupMapping {
  idp_group: string;
  role: UserRole;
}

/**
 * @brief OAuth provider config from admin API.
 *
 * Used for create/edit forms and provider list.
 */
export interface OAuthProviderResponse {
  id: string;
  provider_type: "oidc" | "oauth2";
  display_name: string;
  slug: string;
  icon_url: string | null;
  issuer_url: string | null;
  authorization_endpoint: string;
  token_endpoint: string;
  userinfo_endpoint: string | null;
  jwks_uri: string | null;
  end_session_endpoint: string | null;
  client_id: string;
  group_mappings: Record<string, UserRole>;
  default_role: UserRole;
  group_claim: string;
  scopes: string;
  sub_claim: string;
  email_claim: string;
  name_claim: string;
  avatar_claim: string;
  auto_create_users: boolean;
  enabled: boolean;
  env_seeded?: boolean;
}
