/**
 * @file lib/api/memories.ts
 * @brief "On this day" memories: posts from this date in past years.
 */
import { apiGet } from "./client";
import type { Post } from "./posts";

/** @brief Memories response; `years_ago[i]` belongs to `items[i]`. */
export interface OnThisDay {
  items: Post[];
  years_ago: number[];
}

/** @return memories for the viewer's local date */
export const getOnThisDay = () =>
  apiGet<OnThisDay>("/api/v1/memories/on-this-day");
