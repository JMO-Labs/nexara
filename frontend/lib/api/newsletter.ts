/**
 * @file lib/api/newsletter.ts
 * @brief Printable monthly newsletter REST client (per-viewer content).
 */
import { apiGet, apiPut, seg } from "./client";

export interface NewsPost {
  id: string;
  author_name: string;
  excerpt: string;
  created_at: string;
  reactions: number;
  comments: number;
  pinned: boolean;
  media_ids: string[];
}

export interface NewsPhoto {
  media_id: string;
  post_id: string;
  alt: string | null;
}

export interface NewsPerson {
  name: string;
  date: string;
  link: string;
}

export interface Newsletter {
  month: string;
  community_name: string;
  top_posts: NewsPost[];
  photos: NewsPhoto[];
  birthdays: NewsPerson[];
  remembrances: NewsPerson[];
  new_recipes: { id: string; title: string; author_name: string }[];
  opened_capsules: { id: string; title: string; author_name: string }[];
  events: { id: string; title: string; date: string; place: string | null }[];
  /** Admins only: posts currently hidden, so they can be restored. */
  hidden_posts: NewsPost[];
}

export type OverrideAction = "pin" | "hide" | null;

export const getNewsletter = (month: string) =>
  apiGet<Newsletter>(`/api/v1/newsletter/${seg(month)}`);

export const setNewsletterOverride = (
  month: string,
  post_id: string,
  action: OverrideAction,
) =>
  apiPut<void>(`/api/v1/admin/newsletter/${seg(month)}/overrides`, {
    post_id,
    action,
  });
