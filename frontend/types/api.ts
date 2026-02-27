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
export type UserRole = 'admin' | 'member' | 'viewer'

/**
 * @brief Authenticated user profile returned by GET /users/me.
 *
 * Mirrors backend `UserDetailResponse` schema.
 */
export interface User {
  id: string
  email: string
  username: string
  display_name: string
  email_verified: boolean
  avatar_url: string | null
  bio: string | null
  pronouns: string | null
  location: string | null
  website_url: string | null
  birthday: string | null
  role: UserRole
  totp_enabled: boolean
  storage_used: number
  storage_quota: number
  created_at: string
  updated_at: string
  last_seen_at: string | null
}

/** @brief Login request payload. */
export interface LoginRequest {
  email: string
  password: string
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
  access_token: string | null
  token_type: string
  expires_in: number | null
  requires_2fa: boolean
  two_factor_token: string | null
}

/** @brief Token refresh response (same shape as LoginResponse). */
export interface RefreshResponse {
  access_token: string
  token_type: string
  expires_in: number
}

/** @brief Registration request payload. */
export interface RegisterRequest {
  email: string
  username: string
  display_name: string
  password: string
  invite_token?: string
}

/** @brief Post author summary embedded in post responses. */
export interface PostAuthor {
  id: string
  username: string
  display_name: string
  avatar_url: string | null
}

/** @brief Media attachment on a post. */
export interface PostMedia {
  id: string
  url: string
  thumbnail_url: string | null
  mime_type: string
  width: number | null
  height: number | null
}

/** @brief Reaction summary for a post. */
export interface Reaction {
  emoji: string
  count: number
  reacted_by_me: boolean
}

/** @brief Comment on a post. */
export interface Comment {
  id: string
  content: string
  author: PostAuthor
  parent_id: string | null
  created_at: string
  replies?: Comment[]
}

/** @brief Full post object returned by the feed API. */
export interface Post {
  id: string
  content: string
  author: PostAuthor
  media: PostMedia[]
  reactions: Reaction[]
  comment_count: number
  created_at: string
  updated_at: string
}

/** @brief Cursor-paginated response wrapper. */
export interface PaginatedResponse<T> {
  items: T[]
  cursor: string | null
  has_more: boolean
}

/** @brief Standard API error envelope. */
export interface ApiError {
  error: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
}

/** @brief Toast notification item in UI store. */
export interface ToastItem {
  id: string
  type: 'success' | 'error' | 'info' | 'warning'
  message: string
  duration?: number
}
