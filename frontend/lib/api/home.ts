/**
 * @file lib/api/home.ts
 * @brief API client functions for home-page endpoints:
 *        summary stats and aggregated media feed.
 */

import { apiGet, apiPut } from "./client";
import type { Post } from "./posts";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** @brief Summary stats for the home banner. */
export interface HomeSummary {
  new_posts: number;
  upcoming_events: number;
  unread_notifications: number;
}

/** @brief A single aggregated media item from across visible groups. */
export interface HomeMediaItem {
  media_id: string;
  media: {
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
    status: string;
    created_at: string;
  };
  source: string;
  source_id: string;
  source_title: string | null;
  created_at: string;
}

/** @brief Response envelope for the home media endpoint. */
export interface HomeMediaResponse {
  items: HomeMediaItem[];
  next_cursor: string | null;
}

/** @brief A single activity feed item (possibly aggregated). */
export interface ActivityItem {
  id: string;
  actor_id: string;
  actor_name: string;
  verb: string;
  object_type: string;
  object_id: string;
  container_type: string | null;
  container_title: string | null;
  object_title: string | null;
  count: number;
  created_at: string;
}

/** @brief Response envelope for the activity feed endpoint. */
export interface ActivityFeedResponse {
  items: ActivityItem[];
  next_cursor: string | null;
}

/** @brief Post entry of the unified home feed (post = enriched post dict). */
export interface PostFeedItem {
  kind: "post";
  id: string;
  created_at: string;
  post: Post;
}

/** @brief Activity entry of the unified home feed. */
export interface ActivityFeedItem {
  kind: "activity";
  id: string;
  created_at: string;
  activity: ActivityItem;
}

/** @brief Discriminated union of unified feed items. */
export type FeedItem = PostFeedItem | ActivityFeedItem;

/** @brief Response envelope for the unified home feed. */
export interface HomeFeedResponse {
  items: FeedItem[];
  next_cursor: string | null;
}

/** @brief Persisted home layout stored under settings.home_layout. */
export interface HomeLayout {
  order: string[];
  hidden: string[];
}

/** @brief Minimal shape of the settings response returned after a layout PUT. */
export interface UserSettingsResponse {
  home_layout: HomeLayout | null;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

const HOME = "/api/v1/home";
const SETTINGS = "/api/v1/settings";

/**
 * @brief Fetch home summary stats (new posts, upcoming events, unread notifs).
 * @return HomeSummary object.
 */
export const getHomeSummary = (): Promise<HomeSummary> =>
  apiGet<HomeSummary>(`${HOME}/summary`);

/**
 * @brief Fetch aggregated media items visible to the current user.
 *
 * @param opts Either a numeric limit (legacy) or a struct with limit / scope /
 *             subgroupId. Scope = 'all' | 'community' | 'subgroup' | 'personal'.
 */
export const getHomeMedia = (
  opts:
    | number
    | {
        limit?: number;
        scope?: "all" | "community" | "subgroup" | "personal";
        subgroupId?: string;
      } = 24,
): Promise<HomeMediaResponse> => {
  const params = typeof opts === "number" ? { limit: opts } : opts;
  const limit = params.limit ?? 24;
  const scope = params.scope ?? "all";
  const qs = new URLSearchParams();
  qs.set("limit", String(limit));
  qs.set("scope", scope);
  if (params.subgroupId) qs.set("subgroup_id", params.subgroupId);
  return apiGet<HomeMediaResponse>(`${HOME}/media?${qs.toString()}`);
};

/**
 * @brief Fetch aggregated activity feed visible to the current user.
 *
 * @param opts Either a numeric limit (legacy) or a struct with limit / cursor.
 *             Cursor is ISO8601 datetime for pagination.
 */
export const getHomeActivity = (
  opts:
    | number
    | {
        limit?: number;
        cursor?: string;
      } = 30,
): Promise<ActivityFeedResponse> => {
  const params = typeof opts === "number" ? { limit: opts } : opts;
  const limit = params.limit ?? 30;
  const qs = new URLSearchParams();
  qs.set("limit", String(limit));
  if (params.cursor) qs.set("cursor", params.cursor);
  return apiGet<ActivityFeedResponse>(`${HOME}/activity?${qs.toString()}`);
};

/**
 * @brief Persist the user's home layout via the settings endpoint.
 * @param layout The HomeLayout object with widget instances.
 * @return Updated settings object (we only care about the side-effect).
 */
export const putHomeLayout = (
  layout: HomeLayout,
): Promise<UserSettingsResponse> =>
  apiPut<UserSettingsResponse>(`${SETTINGS}/`, { home_layout: layout });

/**
 * @brief Fetch the unified home feed (posts + activity), newest first.
 * @param cursor ISO datetime cursor from the previous page.
 * @return HomeFeedResponse page.
 */
export const getHomeFeed = (cursor?: string): Promise<HomeFeedResponse> => {
  const qs = new URLSearchParams();
  if (cursor) qs.set("cursor", cursor);
  const q = qs.toString();
  return apiGet<HomeFeedResponse>(`${HOME}/feed${q ? `?${q}` : ""}`);
};
