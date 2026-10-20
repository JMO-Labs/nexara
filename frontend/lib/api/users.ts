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
