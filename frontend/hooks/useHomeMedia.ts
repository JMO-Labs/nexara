/**
 * @file hooks/useHomeMedia.ts
 * @brief TanStack Query hook for aggregated home media carousel data.
 */
'use client';

import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { qk } from '@/lib/query-keys';
import { getHomeMedia, type HomeMediaResponse } from '@/lib/api/home';

/**
 * @brief Fetch aggregated media items visible to the current user.
 *
 * Stale time: 5 minutes. Query key: ['home-media', limit].
 *
 * @param limit Maximum items to fetch (default 24).
 * @return UseQueryResult with HomeMediaResponse data.
 */
export function useHomeMedia(limit?: number): UseQueryResult<HomeMediaResponse> {
  const effectiveLimit = limit ?? 24;
  return useQuery({
    queryKey: qk.home.media(effectiveLimit),
    queryFn: () => getHomeMedia(effectiveLimit),
    staleTime: 5 * 60_000,
  });
}
