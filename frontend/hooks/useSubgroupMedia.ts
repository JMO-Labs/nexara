/**
 * @file hooks/useSubgroupMedia.ts
 * @brief Infinite query hook for subgroup media with source filtering.
 */
"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import {
  getSubgroupMedia,
  MediaListResponse,
  type GetSubgroupMediaParams,
} from "@/lib/api/subgroups";

interface UseSubgroupMediaOptions extends GetSubgroupMediaParams {
  slug: string;
  enabled?: boolean;
}

/**
 * @brief Infinite query hook for paginated subgroup media.
 *
 * @param slug Subgroup slug
 * @param source Media source filter (default: 'all')
 * @param limit Items per page (default: 60)
 * @param enabled When false, the query is paused
 * @returns Infinite query result with media items and pagination
 */
export function useSubgroupMedia({
  slug,
  source = "all",
  limit = 60,
  enabled = true,
}: UseSubgroupMediaOptions) {
  return useInfiniteQuery<MediaListResponse>({
    queryKey: ["subgroup-media", slug, source],
    queryFn: async ({ pageParam = null }) => {
      const params: GetSubgroupMediaParams = {
        source: source as "all" | "post" | "gallery" | "event",
        limit,
        cursor: pageParam as string | null,
      };
      return getSubgroupMedia(slug, params);
    },
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    initialPageParam: null,
    enabled,
  });
}

export default useSubgroupMedia;
