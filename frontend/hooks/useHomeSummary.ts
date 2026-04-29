/**
 * @file hooks/useHomeSummary.ts
 * @brief TanStack Query hook for home page summary stats.
 */
'use client';

import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { qk } from '@/lib/query-keys';
import { getHomeSummary, type HomeSummary } from '@/lib/api/home';

/**
 * @brief Fetch summary stats for the home welcome banner.
 *
 * Stale time: 60 seconds. Query key: ['home-summary'].
 *
 * @return UseQueryResult with HomeSummary data.
 */
export function useHomeSummary(): UseQueryResult<HomeSummary> {
  return useQuery({
    queryKey: qk.home.summary(),
    queryFn: getHomeSummary,
    staleTime: 60_000,
  });
}
