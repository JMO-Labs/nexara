/**
 * @file lib/api/home.ts
 * @brief API client functions for home-page endpoints:
 *        summary stats and aggregated media feed.
 */

import { apiDelete, apiGet, apiPut, seg } from "./client";
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
    is_nsfw?: boolean;
  };
  source: string;
  source_id: string | null;
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
        cursor?: string | null;
      } = 24,
): Promise<HomeMediaResponse> => {
  const params = typeof opts === "number" ? { limit: opts } : opts;
  const limit = params.limit ?? 24;
  const scope = params.scope ?? "all";
  const qs = new URLSearchParams();
  qs.set("limit", String(limit));
  qs.set("scope", scope);
  if (params.subgroupId) qs.set("subgroup_id", params.subgroupId);
  if ("cursor" in params && params.cursor) qs.set("cursor", params.cursor);
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

/** @brief One ranked chat thread on the home page. */
export interface HomeChatThread {
  channel_id: string;
  name: string;
  channel_type: "community" | "subgroup" | "direct";
  subgroup_id: string | null;
  peer: {
    id: string;
    display_name: string;
    avatar_url: string | null;
  } | null;
  last_message: {
    id: string;
    author_name: string | null;
    content: string;
    created_at: string;
  } | null;
  unread_count: number;
  mentions_me: boolean;
  last_activity_at: string;
}

/** @brief Response of GET /home/chats. */
export interface HomeChatsResponse {
  items: HomeChatThread[];
}

/** @brief A person shown in the home people strip. */
export interface HomePerson {
  user_id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
  online: boolean;
  birthday_in_days: number | null;
  last_seen_at: string | null;
  shared_groups: { id: string; name: string; accent_color: string | null }[];
  primary_group_id: string | null;
  shared_events_30d: number;
  /** Pinned by the viewer; pinned people come first, in pin order. */
  favorite?: boolean;
}

/** @brief Response of GET /home/people. */
export interface HomePeopleResponse {
  items: HomePerson[];
}

/** @brief Response of GET /home/needs. */
export interface HomeNeeds {
  rsvps: { event_id: string; title: string; starts_at: string }[];
  polls: { post_id: string; question: string }[];
  prompt: { prompt_post_id: string; post_id: string; title: string } | null;
  list_items: { count: number; list_id: string; list_title: string } | null;
}

/**
 * @brief Fetch ranked chat threads for the home page.
 * @param limit Max threads (1..20).
 */
export const getHomeChats = (limit = 4): Promise<HomeChatsResponse> =>
  apiGet<HomeChatsResponse>(`${HOME}/chats?limit=${limit}`);

/**
 * @brief Fetch people for the home strip.
 * @param limit Max people (1..20).
 */
export const getHomePeople = (limit = 10): Promise<HomePeopleResponse> =>
  apiGet<HomePeopleResponse>(`${HOME}/people?limit=${limit}`);

/**
 * @brief Pin or unpin a person in the viewer's people strip.
 * @param userId person to (un)pin
 * @param on true to pin
 * @return pinned ids in order
 */
export const setFavorite = (userId: string, on: boolean) => {
  const path = `${HOME}/people/favorites/${seg(userId)}`;
  return on
    ? apiPut<{ favorites: string[] }>(path)
    : apiDelete<{ favorites: string[] }>(path);
};

/** @brief Fetch "needs you" items for the home page. */
export const getHomeNeeds = (): Promise<HomeNeeds> =>
  apiGet<HomeNeeds>(`${HOME}/needs`);
