/**
 * @file lib/api/countdowns.ts
 * @brief Countdown API client (create, read, update, delete, follow).
 */
import { apiDelete, apiGet, apiPatch, apiPost, seg } from "./client";

export interface Countdown {
  id: string;
  author_id: string;
  title: string;
  target_date: string;
  target_time: string | null;
  tz: string;
  emoji: string | null;
  cover_media_id: string | null;
  repeat_yearly: boolean;
  visibility: string;
  subgroup_id: string | null;
  post_id: string | null;
  days_left: number;
  next_date: string;
  following: boolean;
  follower_count: number;
}

export interface CountdownInput {
  title: string;
  target_date: string;
  target_time?: string | null;
  tz?: string;
  emoji?: string | null;
  cover_media_id?: string | null;
  repeat_yearly?: boolean;
  visibility?: "community" | "subgroup" | "private";
  subgroup_id?: string | null;
}

const BASE = "/api/v1/countdowns";

export const listCountdowns = () => apiGet<Countdown[]>(BASE);
export const listFollowing = () => apiGet<Countdown[]>(`${BASE}/following`);
export const getCountdown = (id: string) =>
  apiGet<Countdown>(`${BASE}/${seg(id)}`);
export const createCountdown = (b: CountdownInput) =>
  apiPost<Countdown>(BASE, b);
export const updateCountdown = (id: string, b: Partial<CountdownInput>) =>
  apiPatch<Countdown>(`${BASE}/${seg(id)}`, b);
export const deleteCountdown = (id: string) => apiDelete(`${BASE}/${seg(id)}`);
export const followCountdown = (id: string) =>
  apiPost<Countdown>(`${BASE}/${seg(id)}/follow`);
export const unfollowCountdown = (id: string) =>
  apiDelete<Countdown>(`${BASE}/${seg(id)}/follow`);

/**
 * @brief Whole calendar days from the viewer's today to a YYYY-MM-DD date.
 * @param date ISO date (next occurrence)
 * @param now reference instant (viewer's local clock)
 * @return days (0 = today, negative = past)
 */
export function daysUntil(date: string, now: Date = new Date()): number {
  const [y, m, d] = date.split("-").map(Number);
  const target = Date.UTC(y, m - 1, d);
  const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((target - today) / 86_400_000);
}
