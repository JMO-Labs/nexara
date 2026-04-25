/**
 * @file hooks/useSearch.ts
 * @brief TanStack Query hook for global search with scope filtering.
 */
'use client';

import { useQuery } from '@tanstack/react-query';
import { qk } from '@/lib/query-keys';
import { searchAll } from '@/lib/api/search';

export function useGlobalSearch(
  q: string,
  scope: 'all' | 'posts' | 'users' | 'events' | 'comments' = 'all',
) {
  const enabled = q.trim().length >= 2;
  const types = scope === 'all' ? undefined : [scope];

  return useQuery({
    queryKey: qk.search.global(q, scope),
    queryFn: () => searchAll(q, types ? { types } : {}),
    enabled,
    staleTime: 30_000,
  });
}
