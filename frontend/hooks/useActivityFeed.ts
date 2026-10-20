/**
 * @file hooks/useActivityFeed.ts
 * @brief TanStack Query infinite scroll hook for activity feed.
 */
"use client";

import {
  useInfiniteQuery,
  type InfiniteData,
  type UseInfiniteQueryResult,
} from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import {
  getHomeActivity,
  type ActivityFeedResponse,
  type ActivityItem,
} from "@/lib/api/home";

export interface UseActivityFeedParams {
  limit?: number;
}

/**
 * @brief Fetch paginated activity feed with infinite scroll support.
 *
 * Uses cursor-based pagination keyed by created_at of the last item.
 * Stale time: 2 minutes.
 */
export function useActivityFeed(
  arg?: number | UseActivityFeedParams,
): UseInfiniteQueryResult<InfiniteData<ActivityFeedResponse>> {
  const params: UseActivityFeedParams =
    typeof arg === "number" ? { limit: arg } : (arg ?? {});
  const limit = params.limit ?? 30;

  return useInfiniteQuery({
    queryKey: [...qk.home.activity(limit)],
    queryFn: ({ pageParam }) =>
      getHomeActivity({
        limit,
        cursor: pageParam,
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 2 * 60_000,
  });
}

export type { ActivityItem };
