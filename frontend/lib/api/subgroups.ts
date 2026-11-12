/**
 * @file lib/api/subgroups.ts
 * @brief Subgroup REST endpoints + membership management.
 */
import { apiGet, apiPost, apiPut, apiDelete, seg } from "./client";

export interface Subgroup {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  avatar_url: string | null;
  cover_media_id: string | null;
  accent_color?: string | null;
  is_private: boolean;
  join_policy: "open" | "invite_only" | "admin_approval";
  created_by: string | null;
  parent_id: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  my_role: "owner" | "moderator" | "member" | null;
}

export interface SubgroupDetail extends Subgroup {
  member_count: number;
  chat_channel_id: string | null;
  pinned_post_id: string | null;
}

export interface Membership {
  subgroup_id: string;
  user_id: string;
  role: "owner" | "moderator" | "member";
  invited_by: string | null;
  joined_at: string;
  username: string | null;
  display_name: string | null;
  avatar_url: string | null;
}

export interface CreateSubgroupBody {
  name: string;
  slug: string;
  description?: string | null;
  is_private?: boolean;
  join_policy?: "open" | "invite_only" | "admin_approval";
  parent_id?: string | null;
  cover_media_id?: string | null;
  initial_owner_id?: string | null;
}

export interface UpdateSubgroupBody {
  name?: string;
  description?: string | null;
  cover_media_id?: string | null;
  accent_color?: string | null;
  is_private?: boolean;
  join_policy?: "open" | "invite_only" | "admin_approval";
}

const BASE = "/api/v1/subgroups";

export const listSubgroups = () => apiGet<Subgroup[]>(BASE);
export const getSubgroup = (slug: string) =>
  apiGet<SubgroupDetail>(`${BASE}/${seg(slug)}`);
export const createSubgroup = (body: CreateSubgroupBody) =>
  apiPost<SubgroupDetail>(BASE, body);
export const updateSubgroup = (slug: string, body: UpdateSubgroupBody) =>
  apiPut<SubgroupDetail>(`${BASE}/${seg(slug)}`, body);
export const deleteSubgroup = (slug: string) =>
  apiDelete<{ message: string }>(`${BASE}/${seg(slug)}`);
export const joinSubgroup = (slug: string) =>
  apiPost<Membership>(`${BASE}/${seg(slug)}/join`);
export const leaveSubgroup = (slug: string) =>
  apiPost<{ message: string }>(`${BASE}/${seg(slug)}/leave`);
export const listMembers = (slug: string) =>
  apiGet<Membership[]>(`${BASE}/${seg(slug)}/members`);
export const addMember = (slug: string, user_id: string, role = "member") =>
  apiPost<Membership>(`${BASE}/${seg(slug)}/members`, { user_id, role });
export const changeMemberRole = (slug: string, user_id: string, role: string) =>
  apiPost<Membership>(`${BASE}/${seg(slug)}/members/${seg(user_id)}/role`, {
    role,
  });
export const removeMember = (slug: string, user_id: string) =>
  apiDelete<{ message: string }>(
    `${BASE}/${seg(slug)}/members/${seg(user_id)}`,
  );

/**
 * @brief Media response types for subgroup media aggregation.
 */
export interface MediaMetadata {
  id: string;
  filename: string;
  content_type: string;
  storage_key: string;
  thumbnail_key: string | null;
  size_bytes: number;
  width: number | null;
  height: number | null;
  duration_secs: number | null;
  alt_text: string | null;
  status: "processing" | "ready" | "error";
  created_at: string;
}

export interface MediaItem {
  media_id: string;
  media: MediaMetadata;
  source: "post" | "gallery" | "event";
  source_id: string;
  source_title: string | null;
  created_at: string;
}

export interface MediaListResponse {
  items: MediaItem[];
  next_cursor: string | null;
}

export interface GetSubgroupMediaParams {
  source?: "all" | "post" | "gallery" | "event";
  cursor?: string | null;
  limit?: number;
}

export const getSubgroupMedia = (
  slug: string,
  params?: GetSubgroupMediaParams,
) => {
  const qs = new URLSearchParams();
  if (params?.source) qs.set("source", params.source);
  if (params?.cursor) qs.set("cursor", params.cursor);
  if (params?.limit) qs.set("limit", String(params.limit));
  const url = `${BASE}/${seg(slug)}/media${qs.toString() ? `?${qs}` : ""}`;
  return apiGet<MediaListResponse>(url);
};
