/**
 * @file lib/api/kudos.ts
 * @brief Kudos REST client (create + cursor-paginated list).
 */
import { apiGet, apiPost } from "./client";

export interface KudosRecipient {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
}

export interface Kudos {
  id: string;
  recipient_id: string;
  message: string | null;
  author_id: string;
  author_name?: string | null;
  subgroup_id: string | null;
  created_at: string;
  recipient: KudosRecipient | null;
}

export interface KudosPage {
  kudos: Kudos[];
  pagination: { next_cursor?: string | null; has_more?: boolean };
}

export interface CreateKudosBody {
  recipient_id: string;
  message?: string;
  subgroup_id?: string;
}

export const createKudos = (body: CreateKudosBody) =>
  apiPost<Kudos>("/api/v1/kudos", body);

export const listKudos = (cursor?: string | null, limit = 20) => {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (cursor) qs.set("cursor", cursor);
  return apiGet<KudosPage>(`/api/v1/kudos?${qs}`);
};
