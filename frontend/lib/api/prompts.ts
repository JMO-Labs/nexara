/**
 * @file lib/api/prompts.ts
 * @brief Prompts API endpoints for admin CRUD, seeding, and feed posts.
 */
import { apiGet, apiPost, apiPut, apiDelete, seg } from "./client";
import type { Post } from "./posts";

/**
 * @brief Prompt detail within a prompt post.
 */
export interface PromptDetail {
  id: string;
  title: string;
  body: string;
  prompt_type: "standard" | "interest_capture";
  interest_category_slug: string | null;
  interest_capture_hint: string | null;
}

/**
 * @brief Prompt post in feed (pinned prompt instance with response count).
 */
export interface PromptPost {
  id: string;
  post_id: string;
  prompt: PromptDetail;
  response_count: number;
  is_pinned: boolean;
  subgroup_id: string | null;
  subgroup_name: string | null;
  fired_at: string;
  expires_at: string;
}

/**
 * @brief Prompt response model (admin).
 */
export interface PromptResponse {
  id: string;
  title: string;
  body: string;
  frequency: string;
  trigger_month?: number | null;
  trigger_day?: number | null;
  trigger_dow?: number | null;
  enabled: boolean;
  prompt_type: string;
  interest_category_slug?: string | null;
  interest_capture_hint?: string | null;
  created_at: Date;
  updated_at: Date;
  next_fire_at?: Date | null;
  response_count: number;
}

/**
 * @brief Create prompt payload.
 */
export interface PromptCreate {
  title: string;
  body: string;
  frequency: string;
  trigger_month?: number | null;
  trigger_day?: number | null;
  trigger_dow?: number | null;
  prompt_type?: string;
  interest_category_slug?: string | null;
  interest_capture_hint?: string | null;
}

/**
 * @brief Update prompt payload.
 */
export interface PromptUpdate {
  title?: string;
  body?: string;
  frequency?: string;
  trigger_month?: number | null;
  trigger_day?: number | null;
  trigger_dow?: number | null;
  enabled?: boolean;
  prompt_type?: string;
  interest_category_slug?: string | null;
  interest_capture_hint?: string | null;
}

/**
 * @brief List all prompts (admin only).
 * @return Array of PromptResponse
 */
export const listPrompts = () =>
  apiGet<PromptResponse[]>("/api/v1/admin/prompts");

/**
 * @brief Create a new prompt (admin only).
 * @param payload PromptCreate
 * @return PromptResponse
 */
export const createPrompt = (payload: PromptCreate) =>
  apiPost<PromptResponse>("/api/v1/admin/prompts", payload);

/**
 * @brief Update a prompt (admin only).
 * @param promptId Prompt ID
 * @param payload PromptUpdate
 * @return PromptResponse
 */
export const updatePrompt = (promptId: string, payload: PromptUpdate) =>
  apiPut<PromptResponse>(`/api/v1/admin/prompts/${seg(promptId)}`, payload);

/**
 * @brief Delete a prompt (admin only).
 * @param promptId Prompt ID
 * @return Empty response
 */
export const deletePrompt = (promptId: string) =>
  apiDelete<void>(`/api/v1/admin/prompts/${seg(promptId)}`);

/**
 * @brief Seed builtin prompts (admin only).
 * @return Array of created prompts
 */
export const seedBuiltinPrompts = () =>
  apiPost<PromptResponse[]>("/api/v1/admin/prompts/seed", {});

/**
 * @brief Get a prompt post (feed view).
 * @param promptPostId Prompt post ID
 * @return PromptPost
 */
export const getPromptPost = (promptPostId: string) =>
  apiGet<PromptPost>(`/api/v1/prompts/posts/${seg(promptPostId)}`);

/**
 * @brief Get response count for a prompt post (live refresh).
 * @param promptPostId Prompt post ID
 * @return Response count
 */
export const getPromptResponseCount = (promptPostId: string) =>
  apiGet<{ response_count: number }>(
    `/api/v1/prompts/posts/${seg(promptPostId)}/responses`,
  );

/**
 * @brief One page of response posts for a prompt post.
 */
export interface PromptResponsesPage {
  response_count: number;
  items: Post[];
  next_cursor: string | null;
}

/**
 * @brief List response posts for a prompt post (cursor paginated).
 * @param promptPostId Prompt post ID
 * @param cursor Cursor from previous page's next_cursor
 * @param limit Page size
 * @return PromptResponsesPage
 */
export const listPromptResponses = (
  promptPostId: string,
  cursor?: string | null,
  limit = 20,
) => {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (cursor) qs.set("cursor", cursor);
  return apiGet<PromptResponsesPage>(
    `/api/v1/prompts/posts/${seg(promptPostId)}/responses?${qs}`,
  );
};

/**
 * @brief List currently active prompt posts for the home feed.
 * @return Array of PromptPost
 */
export const getActivePrompts = () =>
  apiGet<PromptPost[]>("/api/v1/prompts/active");
