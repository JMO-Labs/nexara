/**
 * @file lib/api/home.ts
 * @brief API client functions for home-page endpoints:
 *        summary stats and aggregated media feed.
 */

import { apiGet, apiPut } from './client';
import type { WidgetInstance } from '@/lib/widgets/registry';

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

/** @brief Persisted home layout stored under settings.home_layout. */
export interface HomeLayout {
  widgets: WidgetInstance[];
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

const HOME = '/api/v1/home';
const SETTINGS = '/api/v1/settings';

/**
 * @brief Fetch home summary stats (new posts, upcoming events, unread notifs).
 * @return HomeSummary object.
 */
export const getHomeSummary = (): Promise<HomeSummary> =>
  apiGet<HomeSummary>(`${HOME}/summary`);

/**
 * @brief Fetch aggregated media items visible to the current user.
 * @param limit Maximum number of items to return (default 24).
 * @return HomeMediaResponse with items array and optional cursor.
 */
export const getHomeMedia = (limit = 24): Promise<HomeMediaResponse> =>
  apiGet<HomeMediaResponse>(`${HOME}/media?limit=${limit}`);

/**
 * @brief Persist the user's home layout via the settings endpoint.
 * @param layout The HomeLayout object with widget instances.
 * @return Updated settings object (we only care about the side-effect).
 */
export const putHomeLayout = (layout: HomeLayout): Promise<unknown> =>
  apiPut<unknown>(`${SETTINGS}/`, { home_layout: layout });
