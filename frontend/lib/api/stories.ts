/**
 * @file lib/api/stories.ts
 * @brief Voice story REST client: requests (ask / answer / decline), the
 *        question bank and a member's Stories tab.
 */
import { apiGet, apiPost, seg } from "./client";
import type { Post } from "./posts";

export interface StoryPerson {
  id: string;
  display_name: string;
}

export interface StoryRequest {
  id: string;
  asker: StoryPerson;
  teller: StoryPerson;
  question: string;
  /** Askers never see "declined"; it reads "open" until expiry. */
  status: "open" | "answered" | "declined" | "expired";
  post_id: string | null;
  created_at: string;
  expires_at: string;
}

export interface StoryRequestList {
  incoming: StoryRequest[];
  outgoing: StoryRequest[];
}

export interface StoryItem {
  question: string | null;
  post: Post;
}

export interface StoryPage {
  items: StoryItem[];
  next_cursor: string | null;
}

const BASE = "/api/v1/stories";

export const listStoryRequests = () =>
  apiGet<StoryRequestList>(`${BASE}/requests`);
export const askStory = (teller_id: string, question: string) =>
  apiPost<StoryRequest>(`${BASE}/requests`, { teller_id, question });
export const answerStory = (id: string, post_id: string) =>
  apiPost<StoryRequest>(`${BASE}/requests/${seg(id)}/answer`, { post_id });
export const declineStory = (id: string) =>
  apiPost<void>(`${BASE}/requests/${seg(id)}/decline`);
export const storyQuestions = () => apiGet<string[]>(`${BASE}/questions`);
export const userStories = (userId: string, cursor: string | null) => {
  const q = new URLSearchParams({ limit: "20" });
  if (cursor) q.set("cursor", cursor);
  return apiGet<StoryPage>(`${BASE}/users/${seg(userId)}?${q.toString()}`);
};
