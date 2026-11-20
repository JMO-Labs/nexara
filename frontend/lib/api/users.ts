/**
 * @file lib/api/users.ts
 * @brief Current-user endpoints used during session bootstrap, plus
 *        community member listing for chat user-pickers.
 */
import { apiGet, apiPatch, apiPost } from "./client";

export interface CurrentUser {
  id: string;
  email: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
  role: string;
  is_admin?: boolean;
  is_active: boolean;
  two_factor_enabled?: boolean;
  tour_completed_at: string | null;
  community_id?: string;
}

export interface UserSummary {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
}

export interface UserListPage {
  items: UserSummary[];
  next_cursor: string | null;
  has_more: boolean;
}

export const getMe = () => apiGet<CurrentUser>("/api/v1/users/me");

export const patchMe = (body: Partial<CurrentUser>) =>
  apiPatch<CurrentUser>("/api/v1/users/me", body);

export const listUsers = (cursor?: string | null, limit = 50) => {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (cursor) qs.set("cursor", cursor);
  return apiGet<UserListPage>(`/api/v1/users?${qs}`);
};

export const completeOnboarding = () =>
  apiPatch<CurrentUser>("/api/v1/users/me/onboarding", {});

export const addInterest = (slug: string) =>
  apiPost<{ slug: string }>("/api/v1/users/me/interests", {
    category_slug: slug,
  });

/** @brief Public profile of a community member (GET /users/{id}). */
export interface UserProfile {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
  bio: string | null;
  title: string | null;
  pronouns: string | null;
  location: string | null;
  website_url: string | null;
  role: string;
  created_at: string;
  last_seen_at: string | null;
}

/** @brief A group shared between the viewer and another member. */
export interface SharedGroup {
  id: string;
  name: string;
  accent_color: string | null;
}

/** @brief One entry of the people directory (privacy already applied). */
export interface DirectoryPerson {
  user_id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
  online: boolean;
  last_seen_at: string | null;
  shared_groups: SharedGroup[];
  primary_group_id: string | null;
}

/** @brief A page of directory entries. */
export interface DirectoryPage {
  items: DirectoryPerson[];
  next_cursor: string | null;
}

/** @brief Directory filter. */
export type DirectoryFilter = "all" | "online" | "groups";

/**
 * @brief Fetch one page of the people directory.
 * @param params search text, filter, page size and cursor
 */
export const getDirectory = (params: {
  q?: string;
  filter?: DirectoryFilter;
  limit?: number;
  cursor?: string | null;
}) => {
  const qs = new URLSearchParams({
    filter: params.filter ?? "all",
    limit: String(params.limit ?? 24),
  });
  if (params.q) qs.set("q", params.q);
  if (params.cursor) qs.set("cursor", params.cursor);
  return apiGet<DirectoryPage>(`/api/v1/users/directory?${qs}`);
};

/**
 * @brief Fetch a member's public profile.
 * @param id user id
 */
export const getUserProfile = (id: string) =>
  apiGet<UserProfile>(`/api/v1/users/${encodeURIComponent(id)}`);
