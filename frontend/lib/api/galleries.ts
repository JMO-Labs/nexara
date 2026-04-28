/**
 * @file lib/api/galleries.ts
 * @brief Galleries + items + collaborators REST endpoints.
 */
import { apiGet, apiPost, apiPatch, apiDelete } from "./client";

export interface Gallery {
  id: string;
  owner_id: string;
  title: string;
  description: string | null;
  cover_media_id: string | null;
  event_id: string | null;
  subgroup_id: string | null;
  visibility: "private" | "subgroup" | "community";
  contribution_policy: "owner_only" | "collaborators" | "community";
  item_count: number;
  is_featured: boolean;
  is_default: boolean;
  is_event_gallery: boolean;
  created_at: string;
  updated_at: string;
}

export interface GalleryItem {
  id: string;
  gallery_id: string;
  media_id: string;
  added_by: string;
  caption: string | null;
  position: number;
  created_at: string;
}

export interface Collaborator {
  gallery_id: string;
  user_id: string;
  invited_by: string | null;
  invited_at: string;
}

export interface GalleryListResponse {
  items: Gallery[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface CreateGalleryBody {
  title: string;
  description?: string | null;
  visibility?: "private" | "subgroup" | "community";
  contribution_policy?: "owner_only" | "collaborators" | "community";
  subgroup_id?: string | null;
  event_id?: string | null;
  cover_media_id?: string | null;
}

const BASE = "/api/v1/galleries";

export interface ListGalleriesParams {
  q?: string;
  sort?: "recent" | "popular" | "oldest";
  featured?: boolean;
}

export const listGalleries = (params?: ListGalleriesParams) => {
  const searchParams = new URLSearchParams();
  if (params?.q) searchParams.append("q", params.q);
  if (params?.sort) searchParams.append("sort", params.sort);
  if (params?.featured !== undefined)
    searchParams.append("featured", String(params.featured));
  const query = searchParams.toString();
  return apiGet<GalleryListResponse>(`${BASE}${query ? `?${query}` : ""}`);
};

export const getGallery = (id: string) => apiGet<Gallery>(`${BASE}/${id}`);
export const createGallery = (body: CreateGalleryBody) =>
  apiPost<Gallery>(BASE, body);
export const updateGallery = (id: string, body: Partial<CreateGalleryBody>) =>
  apiPatch<Gallery>(`${BASE}/${id}`, body);
export const deleteGallery = (id: string) =>
  apiDelete<{ message: string }>(`${BASE}/${id}`);
export const listItems = (id: string) =>
  apiGet<GalleryItem[]>(`${BASE}/${id}/items`);
export const addItem = (id: string, media_id: string, caption?: string) =>
  apiPost<GalleryItem>(`${BASE}/${id}/items`, { media_id, caption });
export const removeItem = (id: string, itemId: string) =>
  apiDelete<{ message: string }>(`${BASE}/${id}/items/${itemId}`);
export const listCollaborators = (id: string) =>
  apiGet<Collaborator[]>(`${BASE}/${id}/collaborators`);
