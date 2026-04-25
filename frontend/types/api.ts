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
  poll?: PollResponse | null;
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
  next_cursor?: string | null;
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

/** @brief Single interest category. */
export interface InterestCategory {
  slug: string;
  label: string;
  description: string | null;
  icon: string | null;
  multi_value: boolean;
  sort_order: number;
}

/** @brief User interest record. */
export interface UserInterest {
  id: string;
  user_id: string;
  category_slug: string;
  value: string;
  source: string;
  confidence: number;
  created_at: string;
}

/** @brief User interests with categories. */
export interface UserInterestsResponse {
  interests: UserInterest[];
  categories: InterestCategory[];
}

/** @brief Interest analytics entry. */
export interface InterestAnalytics {
  category_slug: string;
  value: string;
  count: number;
}

/** @brief VAPID public key response. */
export interface VAPIDPublicKeyResponse {
  public_key: string;
}

/** @brief Push subscription response. */
export interface PushSubscriptionResponse {
  id: string;
  endpoint: string;
  user_agent: string | null;
  created_at: string;
}

/** @brief Branding data from GET /branding/. */
export interface BrandingResponse {
  community_name: string;
  tagline: string | null;
  color_primary: string;
  color_primary_dark: string;
  logo_light_url: string | null;
  logo_dark_url: string | null;
  color_accent?: string;
  color_surface_light?: string;
  color_surface_dark?: string;
  color_text_light?: string;
  color_text_dark?: string;
  font_family?: string;
  font_family_mono?: string;
  email_logo_media_id?: string | null;
  email_footer_text?: string | null;
  email_sender_name?: string | null;
  landing_cta_text?: string | null;
  landing_show_feature_list?: boolean;
  pwa_icon_192_media_id?: string | null;
  pwa_icon_512_media_id?: string | null;
  about_short?: string | null;
  custom_css?: string | null;
  custom_css_enabled?: boolean;
}

/** @brief Contrast warning from PUT /branding/ response. */
export interface ContrastWarning {
  color1: string;
  color2: string;
  ratio: number;
  passes_aa: boolean;
  passes_aaa: boolean;
}

/** @brief Branding update response with contrast warnings. */
export interface BrandingUpdateResponse {
  branding: BrandingResponse;
  contrast_warnings: ContrastWarning[];
}

/** @brief Branding form data for the admin editor. */
export interface BrandingFormData {
  community_name: string;
  tagline: string | null;
  color_primary: string;
  color_primary_dark: string;
  color_accent: string;
  color_surface_light: string;
  color_surface_dark: string;
  color_text_light: string;
  color_text_dark: string;
  font_family: string;
  font_family_mono: string;
  landing_cta_text: string;
}

/** @brief Poll option for creation. */
export interface PollOptionCreate {
  label: string;
  image_media_id?: string | null;
}

/** @brief Poll creation payload. */
export interface PollCreate {
  question: string;
  poll_type: "single" | "multiple" | "yes_no" | "photo";
  options: PollOptionCreate[];
  expires_at?: string | null;
  is_anonymous?: boolean;
  result_visibility?: "after_vote" | "always" | "after_expiry";
}

/** @brief Lightweight voter summary on non-anonymous polls. */
export interface PollVoter {
  id: string;
  display_name: string;
  avatar_url: string | null;
}

/** @brief Poll option with vote count. */
export interface PollOptionResponse {
  id: string;
  label: string;
  image_media_id: string | null;
  position: number;
  vote_count: number;
  voters: PollVoter[];
}

/** @brief Full poll with options. */
export interface PollResponse {
  id: string;
  post_id: string | null;
  poll_type: string;
  question: string;
  options: PollOptionResponse[];
  is_anonymous: boolean;
  result_visibility: string;
  expires_at: string | null;
  closed: boolean;
  total_votes: number;
  user_vote: string[] | null;
  created_at: string;
}

/** @brief Poll results. */
export interface PollResultsResponse {
  poll_id: string;
  options: PollOptionResponse[];
  total_votes: number;
}

/** @brief Link preview metadata. */
export interface LinkPreview {
  id: string;
  url: string;
  title: string | null;
  description: string | null;
  image_url: string | null;
  site_name: string | null;
  provider_type: string | null;
  provider_id: string | null;
}

/** @brief Chat channel kind. */
export type ChannelType = "community" | "subgroup" | "direct";

/**
 * @brief Chat channel from GET /chat/channels.
 *
 * Mirrors backend `ChannelResponse` schema.
 */
export interface ChatChannel {
  id: string;
  community_id: string;
  name: string;
  channel_type: ChannelType;
  subgroup_id: string | null;
  created_at: string;
}

/** @brief Lightweight author block embedded in a chat message. */
export interface ChatMessageAuthor {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
}

/**
 * @brief Single chat message payload.
 *
 * Both REST history items and WS `chat.message` / `chat.updated`
 * frames use this shape. Deleted messages are tombstones with
 * `deleted: true` and `content === "[deleted]"`.
 */
export interface ChatMessage {
  id: string;
  channel_id: string;
  author: ChatMessageAuthor | null;
  content: string;
  edited_at: string | null;
  deleted: boolean;
  created_at: string;
}

/**
 * @brief Cursor-paginated message history response.
 *
 * Mirrors backend `MessageHistoryResponse`. Items are returned
 * newest-first; the `cursor` is an opaque base64 token for the
 * next page of older messages.
 */
export interface MessageHistoryResponse {
  items: ChatMessage[];
  cursor: string | null;
  has_more: boolean;
}

/**
 * @brief DM thread summary from GET /chat/dm.
 *
 * Mirrors backend `DirectMessageThreadResponse`.
 */
export interface DirectMessageThread {
  channel_id: string;
  peer: ChatMessageAuthor;
  created_at: string;
}

/** @brief Inbound chat frame types (client → server). */
export type ChatInboundType = "chat.message" | "chat.typing" | "chat.read";

/** @brief Outbound chat frame types (server → client). */
export type ChatOutboundType =
  | "chat.message"
  | "chat.updated"
  | "chat.deleted"
  | "chat.typing"
  | "chat.read"
  | "chat.error";

/** @brief Tombstone payload for deleted messages (chat.deleted). */
export interface ChatDeletedPayload {
  id: string;
  channel_id: string;
  deleted: true;
  edited_at: string | null;
}

/** @brief Typing indicator payload (both directions). */
export interface ChatTypingPayload {
  channel_id: string;
  user_id?: string;
}

/** @brief Read receipt payload. */
export interface ChatReadPayload {
  channel_id: string;
  message_id: string;
  user_id?: string;
}

/** @brief Error frame payload from the server. */
export interface ChatErrorPayload {
  code: string;
  message: string;
}

/** @brief Subgroup join policy values. */
export type JoinPolicy = "open" | "invite_only" | "admin_approval";

/** @brief Role within a subgroup. */
export type SubgroupRole = "owner" | "moderator" | "member";

/**
 * @brief Summary subgroup representation (list endpoints).
 *
 * Mirrors backend `SubgroupResponse`.
 */
export interface Subgroup {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  avatar_url: string | null;
  is_private: boolean;
  join_policy: JoinPolicy;
  created_by: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * @brief Detailed subgroup with per-viewer state.
 *
 * Mirrors backend `SubgroupDetailResponse`.
 */
export interface SubgroupDetail extends Subgroup {
  member_count: number;
  my_role: SubgroupRole | null;
  chat_channel_id: string | null;
  pinned_post_id: string | null;
}

/**
 * @brief Subgroup membership record with embedded user summary.
 *
 * Mirrors backend `MembershipResponse`.
 */
export interface Membership {
  subgroup_id: string;
  user_id: string;
  role: SubgroupRole;
  invited_by: string | null;
  joined_at: string;
  username: string | null;
  display_name: string | null;
  avatar_url: string | null;
}

/** @brief Payload for creating a subgroup. */
export interface SubgroupCreatePayload {
  name: string;
  slug: string;
  description?: string | null;
  avatar_url?: string | null;
  is_private?: boolean;
  join_policy?: JoinPolicy;
}

/** @brief Partial update payload for a subgroup. */
export interface SubgroupUpdatePayload {
  name?: string;
  description?: string | null;
  avatar_url?: string | null;
  is_private?: boolean;
  join_policy?: JoinPolicy;
}

/** @brief Response from POST /subgroups/{slug}/join. */
export interface JoinSubgroupResponse {
  status: "joined" | "pending";
  role?: SubgroupRole;
  policy?: JoinPolicy;
}
